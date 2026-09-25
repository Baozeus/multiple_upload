from __future__ import annotations

from pathlib import Path
import hashlib
import math
import socket
import sys
import tempfile
import threading
import time
import unittest


CODE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_ROOT))
sys.path.insert(0, str(CODE_ROOT / "ui-handoff" / "client"))

from protocol import recv_exact, recv_json, send_json
from server import FileUploadServer
from multiple_upload_client.tcp_transport import TcpUploadAdapter


class OneConnectionServer:
    def __init__(self, upload_dir: Path) -> None:
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.port = self.listener.getsockname()[1]
        self.server = FileUploadServer("127.0.0.1", self.port, str(upload_dir))
        self.thread = threading.Thread(target=self._serve_once, daemon=True)

    def _serve_once(self) -> None:
        connection, address = self.listener.accept()
        try:
            self.server.handle_client(connection, address)
        finally:
            self.listener.close()

    def __enter__(self) -> "OneConnectionServer":
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.thread.join(timeout=5)
        if self.thread.is_alive():
            self.listener.close()
            raise RuntimeError("TCP smoke server không dừng đúng hạn.")


class DelayedAckService:
    """Real TCP peer that delays only the final server acknowledgement."""

    def __init__(self, upload_dir: Path, ack_delay: float = 0.2) -> None:
        self.upload_dir = upload_dir
        self.ack_delay = ack_delay
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.port = self.listener.getsockname()[1]
        self.payload_received = threading.Event()
        self.thread = threading.Thread(target=self._serve_once, daemon=True)

    def _serve_once(self) -> None:
        connection, _address = self.listener.accept()
        try:
            connection.settimeout(2)
            header = recv_json(connection)
            size = int(header["filesize"])
            name = str(header["filename"])
            send_json(connection, {"status": "OK", "saved_as": name})
            payload = recv_exact(connection, size) if size else b""
            (self.upload_dir / name).write_bytes(payload)
            self.payload_received.set()
            time.sleep(self.ack_delay)
            send_json(
                connection,
                {"status": "SUCCESS", "saved_as": name, "bytes": size},
            )
        finally:
            connection.close()
            self.listener.close()

    def __enter__(self) -> "DelayedAckService":
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is not None:
            self.listener.close()
        self.thread.join(timeout=3)
        if self.thread.is_alive() and exc_type is None:
            self.listener.close()
            raise RuntimeError("Delayed ACK service không dừng đúng hạn.")


class TcpUploadSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.source_dir = self.root / "source"
        self.upload_dir = self.root / "uploads"
        self.source_dir.mkdir()
        self.upload_dir.mkdir()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _upload(self, name: str, content: bytes, conflict: str):
        source = self.source_dir / name
        source.write_bytes(content)
        with OneConnectionServer(self.upload_dir) as server:
            adapter = TcpUploadAdapter("127.0.0.1", server.port, timeout=2)
            progress = []
            result = adapter.upload(
                source,
                conflict=conflict,
                on_progress=lambda percent, speed: progress.append((percent, speed)),
            )
        return result, progress

    def test_tcp_upload_reports_progress_and_writes_file(self) -> None:
        result, progress = self._upload("hello.txt", b"hello over tcp", "rename")
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual((self.upload_dir / "hello.txt").read_bytes(), b"hello over tcp")
        self.assertEqual(progress[-1][0], 100)

    def test_tcp_large_file_reports_independent_progress_samples(self) -> None:
        content = b"x" * (64 * 1024 * 3 + 17)
        result, progress = self._upload("progress.txt", content, "ask")
        percentages = [percent for percent, _speed in progress]
        self.assertEqual(result.status, "SUCCESS")
        self.assertGreaterEqual(len(percentages), 4)
        self.assertEqual(percentages, sorted(percentages))
        self.assertEqual(percentages[-1], 100)
        self.assertTrue(all(speed > 0 for _percent, speed in progress))

    def test_progress_is_monotonic_and_waits_for_server_ack_before_success(self) -> None:
        source = self.source_dir / "ack-state.txt"
        source.write_bytes(bytes(range(256)) * 2000)  # 512,000 bytes = 500 KiB
        progress: list[tuple[int, float]] = []
        waiting_for_ack = threading.Event()

        with DelayedAckService(self.upload_dir) as server:
            adapter = TcpUploadAdapter("127.0.0.1", server.port, timeout=2)
            started = time.monotonic()
            result = adapter.upload(
                source,
                conflict="ask",
                on_progress=lambda percent, speed: progress.append((percent, speed)),
                on_waiting_for_ack=waiting_for_ack.set,
            )
            elapsed = time.monotonic() - started

        percentages = [percent for percent, _speed in progress]
        self.assertTrue(server.payload_received.is_set())
        self.assertTrue(waiting_for_ack.is_set())
        self.assertEqual(result.status, "SUCCESS")
        self.assertGreaterEqual(elapsed, 0.18)
        self.assertGreater(len(percentages), 2)
        self.assertEqual(percentages, sorted(percentages))
        self.assertTrue(all(0 <= percent <= 100 for percent in percentages))
        self.assertTrue(
            all(math.isfinite(speed) and speed >= 0 for _percent, speed in progress)
        )
        self.assertEqual(
            hashlib.sha256(source.read_bytes()).hexdigest(),
            hashlib.sha256((self.upload_dir / source.name).read_bytes()).hexdigest(),
        )

    def test_tcp_rename_overwrite_and_skip(self) -> None:
        (self.upload_dir / "same.txt").write_bytes(b"original")

        renamed, _ = self._upload("same.txt", b"renamed", "rename")
        self.assertEqual(renamed.saved_as, "same(1).txt")
        self.assertEqual((self.upload_dir / "same(1).txt").read_bytes(), b"renamed")

        overwritten, _ = self._upload("same.txt", b"overwritten", "overwrite")
        self.assertEqual(overwritten.status, "SUCCESS")
        self.assertEqual((self.upload_dir / "same.txt").read_bytes(), b"overwritten")

        skipped, progress = self._upload("same.txt", b"must not arrive", "skip")
        self.assertEqual(skipped.status, "SKIPPED")
        self.assertEqual(progress, [])
        self.assertEqual((self.upload_dir / "same.txt").read_bytes(), b"overwritten")

    def test_tcp_ask_reports_duplicate_without_sending_payload(self) -> None:
        (self.upload_dir / "same.txt").write_bytes(b"original")
        duplicate, progress = self._upload("same.txt", b"new", "ask")
        self.assertEqual(duplicate.status, "DUPLICATE")
        self.assertEqual(duplicate.bytes_sent, 0)
        self.assertEqual(progress, [])
        self.assertEqual((self.upload_dir / "same.txt").read_bytes(), b"original")
        self.assertEqual(list(self.upload_dir.glob("*.part")), [])

    def test_legacy_tcp_header_without_conflict_still_renames(self) -> None:
        (self.upload_dir / "legacy.txt").write_bytes(b"existing")
        payload = b"legacy client"
        with OneConnectionServer(self.upload_dir) as server:
            with socket.create_connection(("127.0.0.1", server.port), timeout=2) as client:
                send_json(
                    client,
                    {"filename": "legacy.txt", "filesize": len(payload)},
                )
                self.assertEqual(recv_json(client)["status"], "OK")
                client.sendall(payload)
                result = recv_json(client)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["saved_as"], "legacy(1).txt")
        self.assertEqual((self.upload_dir / "legacy(1).txt").read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
