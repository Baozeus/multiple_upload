from __future__ import annotations

from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest


CODE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_ROOT))
sys.path.insert(0, str(CODE_ROOT / "ui-handoff" / "client"))

from protocol import recv_json, send_json
from server import FileUploadServer
from multiple_upload_client.tcp_transport import (
    ProtocolMismatchError,
    TcpUploadAdapter,
)


class RunningServer:
    def __init__(self, upload_dir: Path, max_concurrent: int = 3) -> None:
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(16)
        self.listener.settimeout(0.1)
        self.port = self.listener.getsockname()[1]
        self.server = FileUploadServer(
            "127.0.0.1", self.port, str(upload_dir), max_concurrent=max_concurrent
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
        self.running = False
        self.listener.close()
        self.thread.join(timeout=2)
        for worker in self.workers:
            worker.join(timeout=2)


class OneShotService:
    def __init__(self, handler) -> None:
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.port = self.listener.getsockname()[1]
        self.handler = handler
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        connection, _ = self.listener.accept()
        try:
            self.handler(connection)
        finally:
            connection.close()
            self.listener.close()

    def __enter__(self) -> "OneShotService":
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.thread.join(timeout=2)


class HealthCheckIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.uploads = self.root / "uploads"
        self.uploads.mkdir()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_udm_health_check_creates_no_upload_artifact(self) -> None:
        with RunningServer(self.uploads) as server:
            result = TcpUploadAdapter("127.0.0.1", server.port, timeout=1).check_server()
        self.assertTrue(result.can_accept_upload)
        self.assertEqual((result.active_uploads, result.upload_limit), (0, 3))
        self.assertEqual(list(self.uploads.iterdir()), [])

    def test_health_check_distinguishes_responsive_server_from_full_slots(self) -> None:
        with RunningServer(self.uploads, max_concurrent=1) as server:
            blocker = socket.create_connection(("127.0.0.1", server.port), timeout=1)
            send_json(
                blocker,
                {"filename": "held.txt", "filesize": 8, "conflict": "rename"},
            )
            self.assertEqual(recv_json(blocker)["status"], "OK")
            result = TcpUploadAdapter(
                "127.0.0.1", server.port, timeout=1
            ).check_server()
            self.assertFalse(result.can_accept_upload)
            self.assertEqual((result.active_uploads, result.upload_limit), (1, 1))
            blocker.close()
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                recovered = TcpUploadAdapter(
                    "127.0.0.1", server.port, timeout=1
                ).check_server()
                if recovered.can_accept_upload:
                    break
                time.sleep(0.01)
            self.assertTrue(recovered.can_accept_upload)
            self.assertEqual(list(self.uploads.glob("*.part")), [])

    def test_invalid_header_releases_bounded_semaphore_exactly_once(self) -> None:
        server = FileUploadServer(
            "127.0.0.1", 0, str(self.uploads), max_concurrent=1
        )
        client, accepted = socket.socketpair()
        try:
            send_json(client, {"filename": "missing-size.txt"})
            server.handle_client(accepted, ("local", 0))
            self.assertEqual(recv_json(client)["status"], "ERROR")
            self.assertTrue(server.upload_limit.acquire(blocking=False))
            server.upload_limit.release()
        finally:
            client.close()

    def test_open_port_with_wrong_protocol_is_not_reported_as_udm(self) -> None:
        def wrong_protocol(connection: socket.socket) -> None:
            recv_json(connection)
            send_json(connection, {
                "status": "HEALTHY",
                "protocol": "OTHER",
                "version": 1,
                "can_accept_upload": True,
                "active_uploads": 0,
                "upload_limit": 1,
            })

        with OneShotService(wrong_protocol) as service:
            with self.assertRaises(ProtocolMismatchError):
                TcpUploadAdapter(
                    "127.0.0.1", service.port, timeout=1
                ).check_server()

    def test_silent_service_times_out_and_can_be_retried(self) -> None:
        def silent(connection: socket.socket) -> None:
            time.sleep(0.25)

        with OneShotService(silent) as service:
            with self.assertRaises(TimeoutError):
                TcpUploadAdapter(
                    "127.0.0.1", service.port, timeout=0.05
                ).check_server()

        with RunningServer(self.uploads) as server:
            result = TcpUploadAdapter(
                "127.0.0.1", server.port, timeout=1
            ).check_server()
        self.assertTrue(result.can_accept_upload)

    def test_server_off_is_reported_as_connection_failure(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        listener.close()
        with self.assertRaises((ConnectionError, TimeoutError)):
            TcpUploadAdapter("127.0.0.1", port, timeout=0.2).check_server()

    def test_upload_still_works_after_health_check(self) -> None:
        source = self.root / "after-check.txt"
        source.write_bytes(b"after health check")
        with RunningServer(self.uploads) as server:
            adapter = TcpUploadAdapter("127.0.0.1", server.port, timeout=1)
            self.assertTrue(adapter.check_server().can_accept_upload)
            result = adapter.upload(source, conflict="ask")
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual((self.uploads / source.name).read_bytes(), source.read_bytes())


if __name__ == "__main__":
    unittest.main()
