"""Repeatable functional, disconnect, stress and performance QA runner.

This runner deliberately exercises public boundaries: the PySide6 UI signal,
the TCP client/server protocol, and files produced by the server.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from typing import Callable


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SCRIPT_PATH = Path(__file__).resolve()
CODE_ROOT = SCRIPT_PATH.parents[2]
REPOSITORY_ROOT = SCRIPT_PATH.parents[3]
CLIENT_ROOT = CODE_ROOT / "ui-handoff" / "client"
sys.path.insert(0, str(CODE_ROOT))
sys.path.insert(0, str(CLIENT_ROOT))

from protocol import recv_json, send_json  # noqa: E402
from multiple_upload_client.config import ClientConfig  # noqa: E402
from multiple_upload_client.history import HistoryStore  # noqa: E402
from multiple_upload_client.models import UploadStatus  # noqa: E402
from multiple_upload_client.queue_manager import UploadQueue  # noqa: E402
from multiple_upload_client.tcp_transport import TcpUploadAdapter  # noqa: E402


MIB = 1024 * 1024


@dataclass(slots=True)
class CaseResult:
    case_id: str
    name: str
    status: str
    duration_seconds: float
    details: dict[str, object]
    error: str = ""


class EvidenceLog:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def write(self, message: str) -> None:
        line = f"[{datetime.now().astimezone().isoformat(timespec='seconds')}] {message}"
        self.lines.append(line)
        print(line, flush=True)


class RunningServer:
    """Start the real server CLI and expose only its TCP port and process id."""

    def __init__(self, upload_dir: Path, log_path: Path) -> None:
        self.upload_dir = upload_dir
        self.log_path = log_path
        self.port = _reserve_local_port()
        self.process: subprocess.Popen[bytes] | None = None
        self._log_stream = None

    def __enter__(self) -> "RunningServer":
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_stream = self.log_path.open("wb")
        environment = os.environ.copy()
        environment["PYTHONUNBUFFERED"] = "1"
        environment["PYTHONIOENCODING"] = "utf-8"
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-B",
                str(CODE_ROOT / "server.py"),
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
                "--dir",
                str(self.upload_dir),
            ],
            cwd=CODE_ROOT,
            stdout=self._log_stream,
            stderr=subprocess.STDOUT,
            env=environment,
        )
        self._wait_until_ready()
        return self

    @property
    def pid(self) -> int:
        if self.process is None:
            raise RuntimeError("Server chưa chạy.")
        return self.process.pid

    def _wait_until_ready(self) -> None:
        deadline = time.monotonic() + 8
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            if self.process is not None and self.process.poll() is not None:
                raise RuntimeError(f"Server dừng sớm với mã {self.process.returncode}.")
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.5) as conn:
                    send_json(
                        conn,
                        {"filename": "qa-readiness.txt", "filesize": 0, "conflict": "overwrite"},
                    )
                    acknowledgement = recv_json(conn)
                    result = recv_json(conn)
                    if acknowledgement.get("status") == "OK" and result.get("status") == "SUCCESS":
                        (self.upload_dir / "qa-readiness.txt").unlink(missing_ok=True)
                        return
            except (ConnectionError, OSError, TimeoutError, ValueError) as error:
                last_error = error
                time.sleep(0.05)
        raise RuntimeError(f"Server không sẵn sàng trong 8 giây: {last_error}")

    def __exit__(self, exc_type, exc_value, exc_traceback) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if self._log_stream is not None:
            self._log_stream.close()


def _reserve_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(MIB), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[index]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _run_case(
    evidence_log: EvidenceLog,
    case_id: str,
    name: str,
    action: Callable[[], dict[str, object]],
) -> CaseResult:
    started = time.perf_counter()
    try:
        details = action()
        result = CaseResult(
            case_id=case_id,
            name=name,
            status="PASS",
            duration_seconds=round(time.perf_counter() - started, 6),
            details=details,
        )
        evidence_log.write(f"{case_id} PASS — {name}")
        return result
    except Exception as error:  # noqa: BLE001 - the report must preserve every failure
        result = CaseResult(
            case_id=case_id,
            name=name,
            status="FAIL",
            duration_seconds=round(time.perf_counter() - started, 6),
            details={},
            error=f"{type(error).__name__}: {error}\n{traceback.format_exc()}",
        )
        evidence_log.write(f"{case_id} FAIL — {name}: {type(error).__name__}: {error}")
        return result


def _raw_request(
    port: int,
    header: dict[str, object],
    payload: bytes = b"",
    read_final: bool = False,
) -> tuple[dict[str, object], dict[str, object] | None]:
    with socket.create_connection(("127.0.0.1", port), timeout=3) as connection:
        connection.settimeout(3)
        send_json(connection, header)
        first = recv_json(connection)
        final = None
        if first.get("status") == "OK" and payload:
            connection.sendall(payload)
        if first.get("status") == "OK" and read_final:
            final = recv_json(connection)
        return first, final


def _functional_tests(
    evidence_dir: Path,
    work_dir: Path,
    evidence_log: EvidenceLog,
) -> list[CaseResult]:
    source_dir = work_dir / "functional-source"
    upload_dir = work_dir / "functional-uploads"
    source_dir.mkdir(parents=True)
    server_log = evidence_dir / "server-functional.log"
    results: list[CaseResult] = []

    with RunningServer(upload_dir, server_log) as server:
        adapter = TcpUploadAdapter("127.0.0.1", server.port, timeout=5)

        def ui_end_to_end() -> dict[str, object]:
            from PySide6.QtGui import QFontDatabase
            from PySide6.QtWidgets import QApplication
            from multiple_upload_client.main_window import MainWindow

            source = source_dir / "ui-dropped.txt"
            source.write_bytes(b"uploaded from the public UI drop signal")
            history_path = evidence_dir / "ui-history.json"
            history_store = HistoryStore(history_path)
            config = ClientConfig(
                transport="tcp",
                tcp_host="127.0.0.1",
                tcp_port=server.port,
                base_url="",
                upload_endpoint="/api/uploads",
                allow_mock_fallback=False,
                max_concurrent=3,
                conflict_policy="rename",
            )
            app = QApplication.instance() or QApplication([])
            for font_path in (
                Path(r"C:\Windows\Fonts\segoeui.ttf"),
                Path(r"C:\Windows\Fonts\segoeuib.ttf"),
            ):
                if font_path.is_file():
                    QFontDatabase.addApplicationFont(str(font_path))
            window = MainWindow(config, history_store)
            window.show()
            app.processEvents()
            window.drop_zone.files_dropped.emit([str(source)])

            deadline = time.monotonic() + 8
            terminal_item = None
            while time.monotonic() < deadline:
                app.processEvents()
                items = list(window.coordinator.queue.items.values())
                if items and items[0].status in {UploadStatus.COMPLETED, UploadStatus.ERROR}:
                    terminal_item = items[0]
                    break
                time.sleep(0.01)

            _assert(terminal_item is not None, "UI không đạt trạng thái kết thúc trong 8 giây.")
            _assert(terminal_item.status is UploadStatus.COMPLETED, terminal_item.detail)
            _assert(terminal_item.progress == 100, "UI không hiển thị tiến trình 100%.")
            destination = upload_dir / source.name
            _assert(destination.read_bytes() == source.read_bytes(), "File qua UI bị sai nội dung.")
            records = history_store.list_records()
            _assert(len(records) == 1, "Lịch sử UI không ghi đúng một kết quả.")
            screenshot = evidence_dir / "ui-upload-completed.png"
            _assert(window.grab().save(str(screenshot), "PNG"), "Không lưu được ảnh UI.")
            title = window.windowTitle()
            window.close()
            app.processEvents()
            return {
                "window_title": title,
                "status": terminal_item.status.value,
                "progress_percent": terminal_item.progress,
                "saved_file": destination.name,
                "history_records": len(records),
                "screenshot": screenshot.name,
            }

        results.append(
            _run_case(
                evidence_log,
                "F01",
                "Kéo-thả qua UI, upload TCP, tiến trình và lịch sử",
                ui_end_to_end,
            )
        )

        def supported_formats() -> dict[str, object]:
            extensions = [".txt", ".pdf", ".jpg", ".jpeg", ".doc", ".docx"]
            for index, extension in enumerate(extensions):
                source = source_dir / f"supported-{index}{extension}"
                payload = f"format={extension};case={index}".encode("utf-8")
                source.write_bytes(payload)
                result = adapter.upload(source)
                _assert(result.status == "SUCCESS", f"Upload {extension} không thành công.")
                _assert((upload_dir / source.name).read_bytes() == payload, f"Sai dữ liệu {extension}.")
            return {"formats": extensions, "count": len(extensions)}

        results.append(_run_case(evidence_log, "F02", "Upload đủ định dạng được hỗ trợ", supported_formats))

        def progress_reporting() -> dict[str, object]:
            source = source_dir / "progress.txt"
            source.write_bytes((b"UDM10-PROGRESS-" * 70000)[:MIB])
            samples: list[tuple[int, float]] = []
            result = adapter.upload(source, on_progress=lambda percent, speed: samples.append((percent, speed)))
            _assert(result.status == "SUCCESS", "Upload đo tiến trình thất bại.")
            _assert(bool(samples), "Không có mẫu tiến trình.")
            _assert(samples[-1][0] == 100, "Mẫu tiến trình cuối không phải 100%.")
            _assert(all(0 <= percent <= 100 for percent, _ in samples), "Phần trăm ngoài khoảng 0–100.")
            return {"samples": len(samples), "final_percent": samples[-1][0]}

        results.append(_run_case(evidence_log, "F03", "Báo tiến trình riêng cho file", progress_reporting))

        def conflict_policies() -> dict[str, object]:
            destination = upload_dir / "conflict.txt"
            destination.write_bytes(b"original")
            source = source_dir / "conflict.txt"

            source.write_bytes(b"renamed")
            renamed = adapter.upload(source, conflict="rename")
            _assert(renamed.saved_as == "conflict(1).txt", "Rename không tạo tên kế tiếp.")
            _assert((upload_dir / "conflict(1).txt").read_bytes() == b"renamed", "Sai file rename.")

            source.write_bytes(b"overwritten")
            overwritten = adapter.upload(source, conflict="overwrite")
            _assert(overwritten.status == "SUCCESS", "Overwrite thất bại.")
            _assert(destination.read_bytes() == b"overwritten", "Overwrite không thay nội dung.")

            source.write_bytes(b"must-not-arrive")
            skipped = adapter.upload(source, conflict="skip")
            _assert(skipped.status == "SKIPPED", "Skip không trả trạng thái SKIPPED.")
            _assert(destination.read_bytes() == b"overwritten", "Skip đã làm đổi file hiện hữu.")
            return {
                "rename": renamed.saved_as,
                "overwrite": overwritten.status,
                "skip": skipped.status,
            }

        results.append(_run_case(evidence_log, "F04", "Xử lý trùng tên rename/overwrite/skip", conflict_policies))

        def reject_extension() -> dict[str, object]:
            source = source_dir / "blocked.exe"
            source.write_bytes(b"not allowed")
            try:
                adapter.upload(source)
            except ValueError as error:
                return {"rejected": source.name, "message": str(error)}
            raise AssertionError("Client đã chấp nhận định dạng .exe.")

        results.append(_run_case(evidence_log, "F05", "Từ chối định dạng không hợp lệ", reject_extension))

        def reject_missing_file() -> dict[str, object]:
            missing = source_dir / "missing.txt"
            try:
                adapter.upload(missing)
            except FileNotFoundError as error:
                return {"rejected": missing.name, "message": str(error)}
            raise AssertionError("Client đã chấp nhận đường dẫn không tồn tại.")

        results.append(_run_case(evidence_log, "F06", "Từ chối file không tồn tại", reject_missing_file))

        def reject_invalid_policy() -> dict[str, object]:
            source = source_dir / "policy.txt"
            source.write_bytes(b"policy")
            try:
                adapter.upload(source, conflict="invalid")
            except ValueError as error:
                return {"policy": "invalid", "message": str(error)}
            raise AssertionError("Client đã chấp nhận conflict policy không hợp lệ.")

        results.append(_run_case(evidence_log, "F07", "Từ chối chính sách trùng tên sai", reject_invalid_policy))

        def reject_missing_header_field() -> dict[str, object]:
            response, _ = _raw_request(server.port, {"filesize": 10})
            _assert(response.get("status") == "ERROR", "Server không từ chối header thiếu filename.")
            return {"server_status": response.get("status"), "message": str(response.get("message"))}

        results.append(_run_case(evidence_log, "F08", "Server từ chối header thiếu dữ liệu", reject_missing_header_field))

        def reject_negative_size() -> dict[str, object]:
            response, _ = _raw_request(server.port, {"filename": "negative.txt", "filesize": -1})
            _assert(response.get("status") == "ERROR", "Server không từ chối filesize âm.")
            return {"server_status": response.get("status"), "message": str(response.get("message"))}

        results.append(_run_case(evidence_log, "F09", "Server từ chối dung lượng âm", reject_negative_size))

        def contain_traversal_name() -> dict[str, object]:
            payload = b"contained"
            first, final = _raw_request(
                server.port,
                {"filename": "../escape.txt", "filesize": len(payload), "conflict": "overwrite"},
                payload,
                read_final=True,
            )
            _assert(first.get("status") == "OK", "Server không xử lý được tên traversal an toàn.")
            _assert(final is not None and final.get("status") == "SUCCESS", "Upload traversal không kết thúc.")
            _assert((upload_dir / "escape.txt").read_bytes() == payload, "File không nằm trong upload dir.")
            _assert(not (upload_dir.parent / "escape.txt").exists(), "Path traversal thoát khỏi upload dir.")
            return {"input_name": "../escape.txt", "saved_as": final.get("saved_as")}

        results.append(_run_case(evidence_log, "F10", "Chặn path traversal trong tên file", contain_traversal_name))

        def abrupt_disconnect_cleanup() -> dict[str, object]:
            final_path = upload_dir / "disconnect.txt"
            with socket.create_connection(("127.0.0.1", server.port), timeout=3) as connection:
                connection.settimeout(3)
                send_json(
                    connection,
                    {"filename": final_path.name, "filesize": 4 * MIB, "conflict": "overwrite"},
                )
                acknowledgement = recv_json(connection)
                _assert(acknowledgement.get("status") == "OK", "Server không nhận header disconnect.")
                connection.sendall(b"partial-data" * 4096)

            deadline = time.monotonic() + 5
            partials: list[Path] = []
            while time.monotonic() < deadline:
                partials = list(upload_dir.glob(".udm10-upload-*.part"))
                if not partials and not final_path.exists():
                    break
                time.sleep(0.05)
            _assert(not final_path.exists(), "Server đã công bố file chưa nhận đủ dữ liệu.")
            _assert(not partials, "Server còn để lại file .part sau khi mất kết nối.")
            return {
                "declared_bytes": 4 * MIB,
                "sent_bytes": len(b"partial-data" * 4096),
                "partial_files_remaining": len(partials),
            }

        results.append(
            _run_case(
                evidence_log,
                "F11",
                "Ngắt kết nối đột ngột và dọn file tạm",
                abrupt_disconnect_cleanup,
            )
        )

        def connection_refused() -> dict[str, object]:
            source = source_dir / "no-server.txt"
            source.write_bytes(b"connection refused")
            unused_port = _reserve_local_port()
            unavailable = TcpUploadAdapter("127.0.0.1", unused_port, timeout=0.5)
            try:
                unavailable.upload(source)
            except (ConnectionError, TimeoutError) as error:
                return {"port": unused_port, "message": str(error)}
            raise AssertionError("Client không báo lỗi khi Server không lắng nghe.")

        results.append(_run_case(evidence_log, "F12", "Báo lỗi khi Server không sẵn sàng", connection_refused))

        def zero_byte_file() -> dict[str, object]:
            source = source_dir / "empty.txt"
            source.write_bytes(b"")
            progress: list[tuple[int, float]] = []
            result = adapter.upload(source, on_progress=lambda percent, speed: progress.append((percent, speed)))
            _assert(result.status == "SUCCESS", "File rỗng upload thất bại.")
            _assert((upload_dir / source.name).exists(), "Server không tạo file rỗng.")
            _assert(progress == [(100, 0.0)], "Progress file rỗng không kết thúc ở 100%.")
            return {"bytes": 0, "progress": progress[-1][0]}

        results.append(_run_case(evidence_log, "F13", "Upload file rỗng hợp lệ", zero_byte_file))

        def queue_concurrency_limit() -> dict[str, object]:
            queue_source = source_dir / "queue"
            queue_source.mkdir()
            paths = []
            for index in range(5):
                path = queue_source / f"queued-{index}.txt"
                path.write_bytes(f"queue-{index}".encode("utf-8"))
                paths.append(path)
            queue = UploadQueue(max_concurrent=3)
            added = queue.add_paths(paths)
            active = queue.take_next()
            waiting = [item for item in queue.items.values() if item.status is UploadStatus.WAITING]
            _assert(len(added) == 5, "Không thêm đủ 5 file vào hàng đợi.")
            _assert(len(active) == 3, "Hàng đợi không giữ đúng giới hạn 3 upload đồng thời.")
            _assert(len(waiting) == 2, "Số file chờ sau khi cấp slot không đúng.")
            return {
                "files_added": len(added),
                "active_uploads": len(active),
                "waiting_files": len(waiting),
                "configured_limit": queue.max_concurrent,
            }

        results.append(
            _run_case(
                evidence_log,
                "F14",
                "Hàng đợi FIFO giới hạn 3 upload đồng thời",
                queue_concurrency_limit,
            )
        )

        def one_failure_does_not_stop_other_client() -> dict[str, object]:
            valid_source = source_dir / "isolated-valid.txt"
            valid_source.write_bytes((b"valid-client" * 100000)[:MIB])
            broken_name = "isolated-broken.txt"
            barrier = threading.Barrier(3)

            def broken_client() -> str:
                barrier.wait(timeout=5)
                with socket.create_connection(("127.0.0.1", server.port), timeout=3) as connection:
                    send_json(
                        connection,
                        {"filename": broken_name, "filesize": 4 * MIB, "conflict": "overwrite"},
                    )
                    acknowledgement = recv_json(connection)
                    _assert(acknowledgement.get("status") == "OK", "Server không nhận Client lỗi.")
                    connection.sendall(b"broken" * 4096)
                return "disconnected"

            def valid_client() -> str:
                barrier.wait(timeout=5)
                return adapter.upload(valid_source).status

            with ThreadPoolExecutor(max_workers=2) as executor:
                broken_future = executor.submit(broken_client)
                valid_future = executor.submit(valid_client)
                barrier.wait(timeout=5)
                broken_status = broken_future.result(timeout=10)
                valid_status = valid_future.result(timeout=10)

            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if not list(upload_dir.glob(".udm10-upload-*.part")):
                    break
                time.sleep(0.05)
            _assert(valid_status == "SUCCESS", "Client hợp lệ bị ảnh hưởng bởi Client lỗi.")
            _assert(
                (upload_dir / valid_source.name).read_bytes() == valid_source.read_bytes(),
                "Dữ liệu của Client hợp lệ không toàn vẹn.",
            )
            _assert(not (upload_dir / broken_name).exists(), "Client lỗi để lại file hoàn chỉnh.")
            _assert(not list(upload_dir.glob(".udm10-upload-*.part")), "Client lỗi để lại file tạm.")
            return {
                "broken_client": broken_status,
                "valid_client": valid_status,
                "valid_bytes": valid_source.stat().st_size,
            }

        results.append(
            _run_case(
                evidence_log,
                "F15",
                "Một Client lỗi không làm dừng Client khác",
                one_failure_does_not_stop_other_client,
            )
        )

    return results


def _run_regression_suite(evidence_dir: Path, evidence_log: EvidenceLog) -> dict[str, object]:
    started = time.perf_counter()
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "Code/tests", "-v"],
        cwd=REPOSITORY_ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    log_path = evidence_dir / "regression-tests.log"
    log_path.write_text(completed.stdout, encoding="utf-8")
    match = re.search(r"Ran\s+(\d+)\s+tests?", completed.stdout)
    test_count = int(match.group(1)) if match else 0
    status = "PASS" if completed.returncode == 0 else "FAIL"
    result = {
        "status": status,
        "test_count": test_count,
        "exit_code": completed.returncode,
        "duration_seconds": round(time.perf_counter() - started, 6),
        "log": log_path.name,
    }
    evidence_log.write(f"R01 {status} — {test_count} test hồi quy")
    return result


def _performance_test(
    evidence_dir: Path,
    work_dir: Path,
    clients: int,
    file_size_mib: int,
    evidence_log: EvidenceLog,
) -> dict[str, object]:
    source_dir = work_dir / f"load-{clients}-source"
    upload_dir = work_dir / f"load-{clients}-uploads"
    source_dir.mkdir(parents=True)
    payload_size = file_size_mib * MIB
    block = bytes(range(256))
    payload = (block * (payload_size // len(block) + 1))[:payload_size]
    expected_hash = hashlib.sha256(payload).hexdigest()
    sources: list[Path] = []
    for index in range(clients):
        source = source_dir / f"load-{clients}-{index:03d}.txt"
        source.write_bytes(payload)
        sources.append(source)

    log_path = evidence_dir / f"server-load-{clients}.log"
    errors: list[str] = []
    failed_clients: set[str] = set()
    latencies: list[float] = []
    barrier = threading.Barrier(clients + 1)

    with RunningServer(upload_dir, log_path) as server:
        def worker(source: Path) -> tuple[str, str, float, str]:
            barrier.wait(timeout=15)
            started = time.perf_counter()
            try:
                result = TcpUploadAdapter("127.0.0.1", server.port, timeout=30).upload(source)
                return source.name, result.status, time.perf_counter() - started, ""
            except Exception as error:  # noqa: BLE001 - every load failure is evidence
                return source.name, "ERROR", time.perf_counter() - started, f"{type(error).__name__}: {error}"

        with ThreadPoolExecutor(max_workers=clients, thread_name_prefix="qa-client") as executor:
            futures = [executor.submit(worker, source) for source in sources]
            overall_started = time.perf_counter()
            barrier.wait(timeout=15)
            for future in as_completed(futures, timeout=90):
                source_name, status, latency, error = future.result()
                latencies.append(latency)
                if status != "SUCCESS":
                    failed_clients.add(source_name)
                    errors.append(error or f"Unexpected status: {status}")
            duration = time.perf_counter() - overall_started

        for source in sources:
            destination = upload_dir / source.name
            if not destination.is_file():
                failed_clients.add(source.name)
                errors.append(f"Missing destination: {destination.name}")
            elif destination.stat().st_size != payload_size:
                failed_clients.add(source.name)
                errors.append(f"Wrong size: {destination.name}")
            elif _sha256(destination) != expected_hash:
                failed_clients.add(source.name)
                errors.append(f"Wrong SHA-256: {destination.name}")

    error_count = len(failed_clients)
    success_count = clients - error_count
    total_mib = clients * file_size_mib
    result = {
        "clients": clients,
        "file_size_mib": file_size_mib,
        "total_mib": total_mib,
        "duration_seconds": round(duration, 6),
        "throughput_mib_s": round(total_mib / duration, 3),
        "requests_per_second": round(clients / duration, 3),
        "latency_mean_ms": round(statistics.fmean(latencies) * 1000, 3),
        "latency_p50_ms": round(_percentile(latencies, 0.50) * 1000, 3),
        "latency_p95_ms": round(_percentile(latencies, 0.95) * 1000, 3),
        "latency_max_ms": round(max(latencies, default=0.0) * 1000, 3),
        "success_count": success_count,
        "error_count": error_count,
        "error_rate_percent": round(error_count * 100 / clients, 3),
        "errors": errors,
        "server_log": log_path.name,
    }
    evidence_log.write(
        "P{:02d} {} client — {:.3f} MiB/s, p95 {:.3f} ms, lỗi {:.3f}%".format(
            clients,
            clients,
            result["throughput_mib_s"],
            result["latency_p95_ms"],
            result["error_rate_percent"],
        )
    )
    return result


def _windows_total_memory_bytes() -> int | None:
    if os.name != "nt":
        return None
    try:
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.total_physical)
    except (AttributeError, OSError):
        return None
    return None


def _cpu_model() -> str:
    if os.name == "nt":
        try:
            import winreg

            key_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
        except OSError:
            pass
    return platform.processor() or "Không xác định"


def _git_commit() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "Không xác định"


def _system_configuration() -> dict[str, object]:
    total_memory = _windows_total_memory_bytes()
    return {
        "hostname": socket.gethostname(),
        "operating_system": platform.platform(),
        "cpu": _cpu_model(),
        "logical_cpu_count": os.cpu_count(),
        "physical_memory_gib": round(total_memory / (1024**3), 2) if total_memory else None,
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "transport": "TCP loopback 127.0.0.1",
        "server_model": "Một thread cho mỗi kết nối",
        "git_commit": _git_commit(),
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    columns = [
        "clients",
        "file_size_mib",
        "total_mib",
        "duration_seconds",
        "throughput_mib_s",
        "requests_per_second",
        "latency_mean_ms",
        "latency_p50_ms",
        "latency_p95_ms",
        "latency_max_ms",
        "success_count",
        "error_count",
        "error_rate_percent",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _format_details(details: dict[str, object]) -> str:
    return json.dumps(details, ensure_ascii=False, separators=(", ", ": ")).replace("|", "\\|")


def _write_report(
    path: Path,
    run_started: str,
    configuration: dict[str, object],
    regression: dict[str, object],
    functional: list[CaseResult],
    performance: list[dict[str, object]],
    evidence_dir: Path,
) -> None:
    functional_passed = sum(result.status == "PASS" for result in functional)
    regression_passed = regression["status"] == "PASS"
    performance_passed = all(int(result["error_count"]) == 0 for result in performance)
    overall = (
        "PASS"
        if regression_passed and functional_passed == len(functional) and performance_passed
        else "FAIL"
    )
    lines = [
        "# Báo cáo kiểm thử UDM_10 — Multiple Upload",
        "",
        f"- Thời điểm chạy: `{run_started}`",
        f"- Kết luận: **{overall}**",
        f"- Regression: **{regression['test_count']} test — {regression['status']}**",
        f"- Functional: **{functional_passed}/{len(functional)} PASS**",
        f"- Stress/performance: **{len(performance)} mức tải**, "
        f"{'không có lỗi' if performance_passed else 'có lỗi'}",
        "",
        "## Phạm vi và tiêu chí",
        "",
        "Kiểm thử đi qua UI PySide6, TCP Client–Server và kết quả file trên filesystem. "
        "Functional đạt khi hành vi quan sát được đúng yêu cầu. Stress/performance đạt về "
        "độ tin cậy khi mọi Client hoàn tất, dữ liệu đúng SHA-256 và tỷ lệ lỗi bằng 0%. "
        "Đề tài chưa quy định SLA thời gian nên latency/throughput được ghi nhận làm baseline.",
        "",
        "## Cấu hình máy và môi trường",
        "",
        "| Thuộc tính | Giá trị |",
        "|---|---|",
    ]
    for key, value in configuration.items():
        lines.append(f"| {key} | {str(value).replace('|', '/')} |")

    lines.extend(
        [
            "",
            "## Kết quả test hồi quy",
            "",
            "| Bộ test | Số test | Kết quả | Thời gian (giây) | Log |",
            "|---|---:|---:|---:|---|",
            f"| `unittest discover -s Code/tests` | {regression['test_count']} | "
            f"**{regression['status']}** | {regression['duration_seconds']} | "
            f"`{regression['log']}` |",
            "",
            "## Dữ liệu đầu vào và cách thực hiện",
            "",
            "- Functional: file nhỏ cho 6 định dạng hợp lệ; file 1 MiB cho progress; "
            "header thiếu trường, dung lượng âm, `.exe`, đường dẫn không tồn tại và tên traversal.",
            "- Mất kết nối: khai báo file 4 MiB, chỉ gửi một phần rồi đóng socket đột ngột; "
            "kiểm tra không có file hoàn chỉnh hoặc `.part` còn sót.",
            "- Performance: mỗi Client gửi một file dữ liệu nhị phân xác định qua TCP loopback; "
            "các Client bắt đầu đồng thời bằng barrier.",
            "- Xác minh: trạng thái TCP, nội dung/size/SHA-256 file đích, tiến trình UI và lịch sử JSON.",
            "",
            "## Kết quả functional",
            "",
            "| ID | Kịch bản | Kết quả | Thời gian (giây) | Chi tiết |",
            "|---|---|---:|---:|---|",
        ]
    )
    for result in functional:
        details = _format_details(result.details) if result.details else result.error.splitlines()[0]
        lines.append(
            f"| {result.case_id} | {result.name} | **{result.status}** | "
            f"{result.duration_seconds:.6f} | {details} |"
        )

    lines.extend(
        [
            "",
            "## Kết quả stress và performance",
            "",
            "| Client đồng thời | Dung lượng/file (MiB) | Tổng (MiB) | Thời gian (s) | "
            "Throughput (MiB/s) | Req/s | Mean (ms) | P50 (ms) | P95 (ms) | Max (ms) | Lỗi |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for result in performance:
        lines.append(
            "| {clients} | {file_size_mib} | {total_mib} | {duration_seconds} | "
            "{throughput_mib_s} | {requests_per_second} | {latency_mean_ms} | "
            "{latency_p50_ms} | {latency_p95_ms} | {latency_max_ms} | "
            "{error_count} ({error_rate_percent}%) |".format(**result)
        )

    lines.extend(
        [
            "",
            "## Bằng chứng",
            "",
            f"Thư mục bằng chứng: `{evidence_dir.relative_to(REPOSITORY_ROOT).as_posix()}`",
            "",
            "- `functional-results.json`: kết quả chi tiết từng case.",
            "- `regression-results.json` và `regression-tests.log`: kết quả 17 test có sẵn.",
            "- `performance-results.json` và `.csv`: số liệu hai mức tải.",
            "- `server-functional.log`: log functional và lỗi mất kết nối.",
            "- `server-load-*.log`: log Server cho từng mức tải.",
            "- `ui-upload-completed.png`: ảnh UI sau khi upload hoàn tất.",
            "- `run-summary.log`: log điều phối toàn bộ lần chạy.",
            "- `manifest-sha256.json`: mã kiểm tra tính toàn vẹn bằng chứng.",
            "",
            "## Giới hạn",
            "",
            "Kết quả performance chạy trên loopback của một máy, nên chưa bao gồm packet loss, "
            "băng thông hoặc độ trễ mạng thật. Khi demo qua LAN cần chạy lại cùng runner hoặc "
            "một công cụ tải tương đương trên hai máy và ghi riêng cấu hình mạng.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_manifest(evidence_dir: Path) -> None:
    manifest: list[dict[str, object]] = []
    for path in sorted(evidence_dir.iterdir(), key=lambda item: item.name):
        if path.is_file() and path.name != "manifest-sha256.json":
            manifest.append(
                {"file": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)}
            )
    (evidence_dir / "manifest-sha256.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chạy functional, stress và performance QA.")
    parser.add_argument(
        "--clients",
        type=int,
        nargs="+",
        default=[5, 20],
        help="Các mức Client đồng thời, mặc định: 5 20",
    )
    parser.add_argument(
        "--file-size-mib",
        type=int,
        default=2,
        help="Dung lượng mỗi file performance theo MiB, mặc định: 2",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Thư mục bằng chứng; mặc định tạo mới dưới docs/test-evidence/",
    )
    arguments = parser.parse_args()
    if len(arguments.clients) < 2 or any(value < 1 for value in arguments.clients):
        parser.error("Cần ít nhất hai mức tải và mỗi mức phải có từ 1 Client.")
    if arguments.file_size_mib < 1:
        parser.error("--file-size-mib phải từ 1 trở lên.")
    return arguments


def main() -> int:
    arguments = _parse_arguments()
    run_started = datetime.now().astimezone().isoformat(timespec="seconds")
    if arguments.output_dir is None:
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        evidence_dir = REPOSITORY_ROOT / "docs" / "test-evidence" / run_id
    else:
        evidence_dir = arguments.output_dir.resolve()
    evidence_dir.mkdir(parents=True, exist_ok=False)

    evidence_log = EvidenceLog()
    evidence_log.write(f"Bắt đầu QA, bằng chứng: {evidence_dir}")
    configuration = _system_configuration()

    with tempfile.TemporaryDirectory(prefix="udm10-qa-") as temporary:
        work_dir = Path(temporary)
        regression = _run_regression_suite(evidence_dir, evidence_log)
        functional = _functional_tests(evidence_dir, work_dir, evidence_log)
        performance = [
            _performance_test(
                evidence_dir,
                work_dir,
                clients,
                arguments.file_size_mib,
                evidence_log,
            )
            for clients in arguments.clients
        ]

    (evidence_dir / "functional-results.json").write_text(
        json.dumps([asdict(result) for result in functional], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (evidence_dir / "regression-results.json").write_text(
        json.dumps(regression, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (evidence_dir / "performance-results.json").write_text(
        json.dumps(performance, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_csv(evidence_dir / "performance-results.csv", performance)
    report_path = evidence_dir / "QA_TEST_REPORT.md"
    _write_report(
        report_path,
        run_started,
        configuration,
        regression,
        functional,
        performance,
        evidence_dir,
    )
    evidence_log.write(f"Báo cáo: {report_path}")
    (evidence_dir / "run-summary.log").write_text(
        "\n".join(evidence_log.lines) + "\n",
        encoding="utf-8",
    )
    _write_manifest(evidence_dir)

    functional_ok = all(result.status == "PASS" for result in functional)
    regression_ok = regression["status"] == "PASS"
    performance_ok = all(int(result["error_count"]) == 0 for result in performance)
    print(f"REPORT_PATH={report_path}")
    return 0 if regression_ok and functional_ok and performance_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
