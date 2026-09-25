from __future__ import annotations

import hashlib
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication


CODE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_ROOT))
sys.path.insert(0, str(CODE_ROOT / "ui-handoff" / "client"))

from server import FileUploadServer
from multiple_upload_client.config import ClientConfig
from multiple_upload_client.models import UploadStatus
from multiple_upload_client.tcp_transport import TcpUploadAdapter
from multiple_upload_client.uploader import UploadCoordinator


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_config(port: int) -> ClientConfig:
    return ClientConfig(
        transport="tcp",
        tcp_host="127.0.0.1",
        tcp_port=port,
        base_url="",
        upload_endpoint="/api/uploads",
        allow_mock_fallback=False,
        max_concurrent=3,
        max_upload_size=512_000,
        conflict_policy="rename",
    )


class GatedFileUploadServer(FileUploadServer):
    """Test-only slow receiver; production runtime never sleeps."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.release = threading.Event()
        self.three_started = threading.Event()
        self._seen_lock = threading.Lock()
        self.first_chunk_names: list[str] = []

    def on_chunk_received(self, filename: str, received: int, total: int) -> None:
        if received <= 0:
            return
        should_wait = False
        with self._seen_lock:
            if filename not in self.first_chunk_names:
                self.first_chunk_names.append(filename)
                should_wait = len(self.first_chunk_names) <= 3
                if len(self.first_chunk_names) == 3:
                    self.three_started.set()
        if should_wait:
            self.release.wait(3)


class FailingOneFileServer(FileUploadServer):
    def on_chunk_received(self, filename: str, received: int, total: int) -> None:
        if filename == "fail.txt" and received > 0:
            raise ConnectionError("Lỗi ghi mô phỏng dành riêng cho kiểm thử")


class RunningServer:
    def __init__(
        self,
        upload_dir: Path,
        server_type=FileUploadServer,
        port: int = 0,
    ) -> None:
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("127.0.0.1", port))
        self.listener.listen(32)
        self.listener.settimeout(0.1)
        self.port = self.listener.getsockname()[1]
        self.server = server_type(
            "127.0.0.1",
            self.port,
            str(upload_dir),
            max_concurrent=3,
        )
        self.running = True
        self.workers: list[threading.Thread] = []
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while self.running:
            try:
                connection, address = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            worker = threading.Thread(
                target=self.server.handle_client,
                args=(connection, address),
                daemon=True,
            )
            self.workers.append(worker)
            worker.start()

    def __enter__(self) -> "RunningServer":
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        release = getattr(self.server, "release", None)
        if release is not None:
            release.set()
        self.running = False
        self.listener.close()
        self.thread.join(timeout=2)
        for worker in self.workers:
            worker.join(timeout=3)


class TargetTcpIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.sources = self.root / "sources"
        self.uploads = self.root / "uploads"
        self.sources.mkdir()
        self.uploads.mkdir()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def wait_for(self, predicate, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.app.processEvents()
            if predicate():
                return
            time.sleep(0.01)
        self.fail("Điều kiện tích hợp không hoàn tất đúng thời hạn.")

    def make_sources(self, count: int, prefix: str = "fifo") -> list[Path]:
        paths = []
        for index in range(count):
            path = self.sources / f"{prefix}-{index}.txt"
            path.write_bytes(bytes([index + 1]) * (128 * 1024))
            paths.append(path)
        return paths

    def test_tc3_tc10_six_real_uploads_run_in_fifo_waves_of_three(self) -> None:
        paths = self.make_sources(6)
        with RunningServer(self.uploads, GatedFileUploadServer) as running:
            coordinator = UploadCoordinator(make_config(running.port))
            coordinator.add_files([str(path) for path in paths])

            self.wait_for(running.server.three_started.is_set)
            health = TcpUploadAdapter(
                "127.0.0.1", running.port, timeout=1
            ).check_server()
            statuses = [item.status for item in coordinator.queue.items.values()]
            self.assertEqual((health.active_uploads, health.upload_limit), (3, 3))
            self.assertEqual(statuses[:3], [UploadStatus.UPLOADING] * 3)
            self.assertEqual(statuses[3:], [UploadStatus.WAITING] * 3)
            extra_client_source = self.sources / "extra-client.txt"
            extra_client_source.write_bytes(b"must be rejected while server is full")
            with self.assertRaisesRegex(RuntimeError, "đủ 3"):
                TcpUploadAdapter(
                    "127.0.0.1", running.port, timeout=1
                ).upload(extra_client_source, conflict="rename")
            with self.assertRaisesRegex(ValueError, "đang còn tệp"):
                coordinator.update_tcp_endpoint("127.0.0.1", running.port + 1)

            observed_active = 3
            running.server.release.set()
            while not all(
                item.status is UploadStatus.COMPLETED
                for item in coordinator.queue.items.values()
            ):
                self.app.processEvents()
                active = sum(
                    item.status is UploadStatus.UPLOADING
                    for item in coordinator.queue.items.values()
                )
                observed_active = max(observed_active, active)
                self.assertLessEqual(active, 3)
                if any(item.status is UploadStatus.ERROR for item in coordinator.queue.items.values()):
                    self.fail("Một upload TCP thật bị lỗi ngoài dự kiến.")
                time.sleep(0.005)

            self.assertEqual(observed_active, 3)
            # FIFO determines which three items enter each wave.  Socket thread
            # scheduling inside a wave is intentionally not ordered.
            self.assertEqual(
                set(running.server.first_chunk_names[:3]),
                {path.name for path in paths[:3]},
            )
            self.assertEqual(
                set(running.server.first_chunk_names[3:]),
                {path.name for path in paths[3:]},
            )

        for source in paths:
            destination = self.uploads / source.name
            self.assertTrue(destination.exists())
            self.assertEqual(sha256(source), sha256(destination))
        self.assertFalse((self.uploads / "extra-client.txt").exists())

    def test_tc10_failed_upload_releases_slot_and_next_file_completes(self) -> None:
        paths = []
        for name in ("fail.txt", "ok-1.txt", "ok-2.txt", "ok-3.txt"):
            path = self.sources / name
            path.write_bytes(name.encode("utf-8") * 4096)
            paths.append(path)

        with RunningServer(self.uploads, FailingOneFileServer) as running:
            coordinator = UploadCoordinator(make_config(running.port))
            coordinator.add_files([str(path) for path in paths])
            self.wait_for(
                lambda: all(
                    item.status in {
                        UploadStatus.COMPLETED,
                        UploadStatus.ERROR,
                    }
                    for item in coordinator.queue.items.values()
                )
            )
            by_name = {item.path.name: item for item in coordinator.queue.items.values()}
            self.assertIs(by_name["fail.txt"].status, UploadStatus.ERROR)
            self.assertTrue(
                all(
                    by_name[name].status is UploadStatus.COMPLETED
                    for name in ("ok-1.txt", "ok-2.txt", "ok-3.txt")
                )
            )

        self.assertFalse((self.uploads / "fail.txt").exists())
        self.assertEqual(list(self.uploads.glob("*.part")), [])
        for source in paths[1:]:
            self.assertEqual(sha256(source), sha256(self.uploads / source.name))

    def test_tc12_alternate_port_health_upload_and_wrong_endpoint(self) -> None:
        source = self.sources / "alternate-port.txt"
        source.write_bytes(b"alternate endpoint" * 4096)

        with RunningServer(self.uploads) as running:
            self.assertNotEqual(running.port, 9000)
            coordinator = UploadCoordinator(make_config(running.port))
            states: list[dict[str, object]] = []
            coordinator.connection_state_changed.connect(states.append)
            self.assertTrue(coordinator.check_connection())
            self.wait_for(lambda: states and states[-1].get("state") == "ready")
            coordinator.add_files([str(source)])
            item = next(iter(coordinator.queue.items.values()))
            self.wait_for(lambda: item.status is UploadStatus.COMPLETED)

            wrong_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            wrong_listener.bind(("127.0.0.1", 0))
            wrong_port = wrong_listener.getsockname()[1]
            wrong_listener.close()
            with self.assertRaises((ConnectionError, TimeoutError)):
                TcpUploadAdapter(
                    "127.0.0.1", wrong_port, timeout=0.2
                ).check_server()

        self.assertEqual(sha256(source), sha256(self.uploads / source.name))

    def test_tc8_offline_file_can_be_retried_after_server_starts(self) -> None:
        source = self.sources / "retry-after-offline.txt"
        source.write_bytes(b"retry payload" * 4096)
        reservation = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
        reservation.close()

        coordinator = UploadCoordinator(make_config(port))
        coordinator.add_files([str(source)])
        item = next(iter(coordinator.queue.items.values()))
        self.wait_for(lambda: item.status is UploadStatus.ERROR)
        self.assertEqual(item.progress, 0)

        with RunningServer(self.uploads, port=port):
            coordinator.retry(item.id)
            self.wait_for(lambda: item.status is UploadStatus.COMPLETED)

        self.assertEqual(sha256(source), sha256(self.uploads / source.name))


if __name__ == "__main__":
    unittest.main()
