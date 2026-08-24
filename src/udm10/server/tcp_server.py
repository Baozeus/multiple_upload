"""Threaded TCP connection lifecycle and control-message dispatch."""

from __future__ import annotations

import socketserver
from pathlib import Path
from typing import Any

from udm10 import __version__
from udm10.config import TcpSettings, UploadPolicySettings
from udm10.protocol import ConnectionClosed, ProtocolError, receive_message, send_message
from udm10.persistence import HistoryRepository, PersistenceError
from udm10.server.file_storage import FileStorage
from udm10.server.upload_service import UploadService
from udm10.server.validation import UploadValidator


class UdmTcpServer(socketserver.ThreadingTCPServer):
    """Thread-per-connection server for lightweight control messages."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        settings: TcpSettings,
        upload_service: UploadService,
        history_repository: HistoryRepository | None = None,
    ):
        self.max_message_bytes = settings.max_control_message_bytes
        self.socket_timeout_seconds = settings.socket_timeout_seconds
        self.upload_service = upload_service
        self.history_repository = history_repository
        super().__init__(server_address, ControlRequestHandler)


class ControlRequestHandler(socketserver.BaseRequestHandler):
    """Handle sequential control frames and file payloads on one connection."""

    server: UdmTcpServer

    def handle(self) -> None:
        self.request.settimeout(self.server.socket_timeout_seconds)
        while True:
            try:
                request = receive_message(
                    self.request,
                    max_payload_bytes=self.server.max_message_bytes,
                )
            except ConnectionClosed:
                return
            except TimeoutError:
                self._send_error("connection_timeout", "Hết thời gian chờ control message.")
                return
            except (OSError, ProtocolError) as exc:
                self._send_error("invalid_request", str(exc))
                return

            try:
                if request.get("type") == "upload.start":
                    response = self.server.upload_service.process(
                        request, self.request, self._send
                    )
                elif request.get("type") == "upload.skip":
                    response = self.server.upload_service.record_skip(request)
                else:
                    response = _dispatch(request, self.server.history_repository)
                self._send(response)
            except (ConnectionError, OSError):
                return

    def _send(self, message: dict[str, Any] | Any) -> None:
        send_message(
            self.request,
            message,
            max_payload_bytes=self.server.max_message_bytes,
        )

    def _send_error(self, code: str, message: str) -> None:
        try:
            self._send({"type": "error", "code": code, "message": message})
        except (ConnectionError, OSError):
            pass


def _dispatch(
    message: dict[str, Any], history_repository: HistoryRepository | None
) -> dict[str, Any]:
    if message.get("type") == "health.check":
        return {
            "type": "health.ok",
            "service": "udm10-server",
            "version": __version__,
        }
    if message.get("type") == "history.list":
        if history_repository is None:
            return {"type": "history.result", "entries": []}
        try:
            records = history_repository.list_files()
        except PersistenceError as exc:
            return {
                "type": "history.error",
                "code": "history_unavailable",
                "message": str(exc),
            }
        entries = []
        for record in records:
            if record.status not in {"completed", "failed", "skipped"}:
                continue
            result = record.status
            if record.status == "completed":
                result = (
                    "renamed"
                    if record.duplicate_policy == "rename"
                    and record.stored_name != record.original_name
                    else "success"
                )
            entries.append(
                {
                    "id": record.id,
                    "name": record.stored_name or record.original_name,
                    "completed_at": (
                        record.completed_at or record.started_at
                    ).isoformat(),
                    "size_bytes": record.size_bytes,
                    "result": result,
                }
            )
        return {"type": "history.result", "entries": entries}
    return {
        "type": "error",
        "code": "unsupported_message",
        "message": "Loại thông điệp chưa được hỗ trợ.",
    }


def create_server(
    settings: TcpSettings,
    *,
    upload_dir: Path | None = None,
    upload_policy: UploadPolicySettings | None = None,
    history_repository: HistoryRepository | None = None,
) -> UdmTcpServer:
    """Create a configured server without starting its event loop."""
    policy = upload_policy or UploadPolicySettings(None, None, None)
    storage = FileStorage(
        upload_dir or Path.cwd() / "uploads",
        chunk_size=settings.file_chunk_size_bytes,
    )
    service = UploadService(
        UploadValidator(policy), storage, history_repository=history_repository
    )
    return UdmTcpServer(
        (settings.bind_host, settings.port),
        settings,
        service,
        history_repository,
    )
