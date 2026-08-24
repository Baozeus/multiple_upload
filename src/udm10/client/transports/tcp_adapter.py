"""Blocking one-file TCP uploader intended to run outside the GUI thread."""

from __future__ import annotations

import socket
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from udm10.client.models.upload import ConflictPolicy, UploadStatus
from udm10.client.models.history import HistoryEntry, HistoryResult
from udm10.protocol import ProtocolError, receive_message, send_message


class TcpUploadError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class TransferProgress:
    bytes_sent: int
    total_bytes: int
    percent: int
    speed_bytes_per_second: float


@dataclass(frozen=True, slots=True)
class UploadOutcome:
    status: UploadStatus
    stored_name: str | None
    bytes_received: int
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class ConflictNotice:
    filename: str


class TcpUploadClient:
    """Stream a file and expose only progress plus its per-file outcome."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        timeout_seconds: float,
        max_control_message_bytes: int,
        chunk_size_bytes: int,
        progress_interval_seconds: float = 0.1,
    ) -> None:
        if chunk_size_bytes <= 0:
            raise ValueError("chunk_size_bytes phải lớn hơn 0.")
        if progress_interval_seconds < 0:
            raise ValueError("progress_interval_seconds không được âm.")
        self._address = (host, port)
        self._timeout = timeout_seconds
        self._max_control = max_control_message_bytes
        self._chunk_size = chunk_size_bytes
        self._progress_interval = progress_interval_seconds

    def upload(
        self,
        source: Path,
        *,
        request_id: str,
        batch_id: str | None = None,
        batch_total: int = 1,
        conflict: ConflictPolicy | None,
        on_progress: Callable[[TransferProgress], None],
    ) -> UploadOutcome | ConflictNotice:
        try:
            total_bytes = source.stat().st_size
        except OSError as exc:
            raise TcpUploadError(
                "local_file_error", "Không thể đọc thông tin tệp nguồn."
            ) from exc

        try:
            with socket.create_connection(
                self._address, timeout=self._timeout
            ) as connection:
                connection.settimeout(self._timeout)
                metadata: dict[str, Any] = {
                    "type": "upload.start",
                    "request_id": request_id,
                    "batch_id": batch_id or request_id,
                    "batch_total": batch_total,
                    "filename": source.name,
                    "size": total_bytes,
                }
                if conflict is not None:
                    metadata["conflict"] = conflict.value
                send_message(
                    connection,
                    metadata,
                    max_payload_bytes=self._max_control,
                )
                first_response = receive_message(
                    connection, max_payload_bytes=self._max_control
                )
                if first_response.get("type") == "upload.result":
                    return _parse_outcome(first_response, request_id)
                if first_response.get("type") == "upload.conflict":
                    if first_response.get("request_id") != request_id:
                        raise TcpUploadError(
                            "unexpected_response", "Máy chủ trả sai mã yêu cầu."
                        )
                    filename = first_response.get("filename")
                    if not isinstance(filename, str):
                        raise TcpUploadError(
                            "unexpected_response", "Máy chủ trả tên tệp không hợp lệ."
                        )
                    return ConflictNotice(filename)
                if first_response != {"type": "upload.ready", "request_id": request_id}:
                    raise TcpUploadError(
                        "unexpected_response", "Server không trả upload.ready hợp lệ."
                    )

                self._send_payload(connection, source, total_bytes, on_progress)
                response = receive_message(
                    connection, max_payload_bytes=self._max_control
                )
                return _parse_outcome(response, request_id)
        except TcpUploadError:
            raise
        except (socket.timeout, TimeoutError) as exc:
            raise TcpUploadError(
                "connection_timeout", "Máy chủ phản hồi quá chậm. Hãy thử lại."
            ) from exc
        except (ConnectionError, OSError, ProtocolError) as exc:
            raise TcpUploadError(
                "connection_error",
                "Không thể kết nối tới máy chủ. Kiểm tra mạng rồi thử lại.",
            ) from exc

    def health_check(self) -> bool:
        try:
            with socket.create_connection(
                self._address, timeout=self._timeout
            ) as connection:
                connection.settimeout(self._timeout)
                send_message(
                    connection,
                    {"type": "health.check"},
                    max_payload_bytes=self._max_control,
                )
                response = receive_message(
                    connection, max_payload_bytes=self._max_control
                )
                return response.get("type") == "health.ok"
        except (ConnectionError, OSError, ProtocolError, TimeoutError):
            return False

    def load_history(self) -> tuple[HistoryEntry, ...]:
        try:
            with socket.create_connection(
                self._address, timeout=self._timeout
            ) as connection:
                connection.settimeout(self._timeout)
                send_message(
                    connection,
                    {"type": "history.list"},
                    max_payload_bytes=self._max_control,
                )
                response = receive_message(
                    connection, max_payload_bytes=self._max_control
                )
        except (socket.timeout, TimeoutError) as exc:
            raise TcpUploadError(
                "history_timeout", "Máy chủ phản hồi quá chậm khi tải lịch sử."
            ) from exc
        except (ConnectionError, OSError, ProtocolError) as exc:
            raise TcpUploadError(
                "history_error", "Không thể tải lịch sử từ máy chủ."
            ) from exc

        if response.get("type") == "history.error":
            message = response.get("message")
            raise TcpUploadError(
                "history_error",
                message if isinstance(message, str) else "Không thể tải lịch sử.",
            )
        if response.get("type") != "history.result":
            raise TcpUploadError("history_error", "Máy chủ trả lịch sử không hợp lệ.")
        rows = response.get("entries")
        if not isinstance(rows, list):
            raise TcpUploadError("history_error", "Danh sách lịch sử không hợp lệ.")
        try:
            return tuple(_parse_history_entry(row) for row in rows)
        except (KeyError, TypeError, ValueError) as exc:
            raise TcpUploadError(
                "history_error", "Dữ liệu lịch sử từ máy chủ không hợp lệ."
            ) from exc

    def record_skip(
        self,
        *,
        request_id: str,
        batch_id: str,
        batch_total: int,
        filename: str,
        size_bytes: int,
    ) -> None:
        try:
            with socket.create_connection(
                self._address, timeout=self._timeout
            ) as connection:
                connection.settimeout(self._timeout)
                send_message(
                    connection,
                    {
                        "type": "upload.skip",
                        "request_id": request_id,
                        "batch_id": batch_id,
                        "batch_total": batch_total,
                        "filename": filename,
                        "size": size_bytes,
                    },
                    max_payload_bytes=self._max_control,
                )
                response = receive_message(
                    connection, max_payload_bytes=self._max_control
                )
        except (ConnectionError, OSError, ProtocolError, TimeoutError) as exc:
            raise TcpUploadError(
                "history_error", "Không thể lưu trạng thái bỏ qua vào lịch sử."
            ) from exc
        outcome = _parse_outcome(response, request_id)
        if outcome.status != UploadStatus.SKIPPED:
            raise TcpUploadError(
                "history_error", "Máy chủ không xác nhận trạng thái bỏ qua."
            )

    def _send_payload(
        self,
        connection: socket.socket,
        source: Path,
        total_bytes: int,
        on_progress: Callable[[TransferProgress], None],
    ) -> None:
        sent = 0
        started_at = time.monotonic()
        last_emitted_at = started_at
        try:
            input_file = source.open("rb")
        except OSError as exc:
            raise TcpUploadError("local_file_error", "Không thể đọc tệp nguồn.") from exc

        with input_file:
            try:
                remaining = total_bytes
                while remaining:
                    try:
                        chunk = input_file.read(min(self._chunk_size, remaining))
                    except OSError as exc:
                        raise TcpUploadError(
                            "local_file_error", "Không thể đọc tệp nguồn."
                        ) from exc
                    if not chunk:
                        raise TcpUploadError(
                            "local_file_changed",
                            "Tệp nguồn ngắn hơn dung lượng đã khai báo.",
                        )
                    try:
                        connection.sendall(chunk)
                    except (ConnectionError, OSError, TimeoutError) as exc:
                        raise TcpUploadError(
                            "connection_error",
                            "Mất kết nối khi đang tải tệp. Kiểm tra mạng rồi thử lại.",
                        ) from exc
                    sent += len(chunk)
                    remaining -= len(chunk)
                    now = time.monotonic()
                    if (
                        now - last_emitted_at >= self._progress_interval
                        or sent == total_bytes
                    ):
                        elapsed = max(now - started_at, 1e-9)
                        on_progress(
                            TransferProgress(
                                bytes_sent=sent,
                                total_bytes=total_bytes,
                                percent=int(sent * 100 / total_bytes),
                                speed_bytes_per_second=sent / elapsed,
                            )
                        )
                        last_emitted_at = now
            except TcpUploadError:
                raise


def _parse_outcome(response: Mapping[str, Any], request_id: str) -> UploadOutcome:
    if (
        response.get("type") != "upload.result"
        or response.get("request_id") != request_id
    ):
        raise TcpUploadError("unexpected_response", "Server trả kết quả sai request_id.")
    status_value = response.get("status")
    try:
        status = UploadStatus(status_value)
    except (TypeError, ValueError) as exc:
        raise TcpUploadError(
            "unexpected_response", "Server trả trạng thái không hợp lệ."
        ) from exc
    if status not in {UploadStatus.COMPLETED, UploadStatus.FAILED, UploadStatus.SKIPPED}:
        raise TcpUploadError("unexpected_response", "Server chưa trả trạng thái cuối.")
    bytes_received = response.get("bytes_received", 0)
    if isinstance(bytes_received, bool) or not isinstance(bytes_received, int):
        raise TcpUploadError("unexpected_response", "bytes_received không hợp lệ.")
    return UploadOutcome(
        status=status,
        stored_name=(
            response.get("filename")
            if isinstance(response.get("filename"), str)
            else None
        ),
        bytes_received=bytes_received,
        error_code=response.get("code") if isinstance(response.get("code"), str) else None,
        error_message=(
            response.get("message")
            if isinstance(response.get("message"), str)
            else None
        ),
    )


def _parse_history_entry(value: Any) -> HistoryEntry:
    if not isinstance(value, Mapping):
        raise TypeError("History entry phải là object.")
    entry_id = value["id"]
    name = value["name"]
    size_bytes = value["size_bytes"]
    if not isinstance(entry_id, str) or not isinstance(name, str):
        raise TypeError("ID hoặc tên lịch sử không hợp lệ.")
    if isinstance(size_bytes, bool) or not isinstance(size_bytes, int):
        raise TypeError("Dung lượng lịch sử không hợp lệ.")
    return HistoryEntry(
        id=entry_id,
        name=name,
        completed_at=datetime.fromisoformat(value["completed_at"]),
        size_bytes=size_bytes,
        result=HistoryResult(value["result"]),
    )
