from __future__ import annotations

from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Code"))
sys.path.insert(0, str(PROJECT_ROOT / "ui-handoff" / "client"))

from protocol import recv_json, send_json
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
