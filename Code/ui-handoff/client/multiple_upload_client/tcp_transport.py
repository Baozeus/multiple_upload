"""Pure-Python TCP Adapter for the existing UDM_10 upload protocol."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import socket
import time
from typing import Callable

from .limits import ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE

HEADER_MAX = 64 * 1024
CHUNK_SIZE = 64 * 1024
DEFAULT_TIMEOUT = 10.0
CONFLICT_POLICIES = frozenset({"ask", "rename", "overwrite", "skip"})
PROTOCOL_NAME = "UDM_10"
PROTOCOL_VERSION = 1


ProgressCallback = Callable[[int, float], None]
AckWaitCallback = Callable[[], None]


@dataclass(frozen=True, slots=True)
class TcpUploadResult:
    status: str
    saved_as: str
    bytes_sent: int
    message: str = ""


@dataclass(frozen=True, slots=True)
class TcpHealthResult:
    can_accept_upload: bool
    active_uploads: int
    upload_limit: int


class ProtocolMismatchError(ConnectionError):
    """Cổng TCP có phản hồi nhưng không nói đúng giao thức UDM_10."""


class TcpUploadAdapter:
    """Upload one file per TCP connection through a small synchronous interface."""

    def __init__(self, host: str, port: int, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def upload(
        self,
        path: str | Path,
        conflict: str = "rename",
        on_progress: ProgressCallback | None = None,
        on_waiting_for_ack: AckWaitCallback | None = None,
    ) -> TcpUploadResult:
        source = Path(path).resolve()
        self._validate_source(source, conflict)
        size = source.stat().st_size
        sent = 0
        started_at = time.monotonic()

        try:
            with socket.create_connection(
                (self.host, self.port), timeout=self.timeout
            ) as connection:
                connection.settimeout(self.timeout)
                _send_json(
                    connection,
                    {
                        "filename": source.name,
                        "filesize": size,
                        "conflict": conflict,
                    },
                )
                acknowledgement = _recv_json(connection)
                if acknowledgement.get("status") == "DUPLICATE":
                    return TcpUploadResult(
                        status="DUPLICATE",
                        saved_as=str(acknowledgement.get("saved_as", source.name)),
                        bytes_sent=0,
                        message=str(
                            acknowledgement.get(
                                "message", "Tên tệp đã tồn tại trên Server."
                            )
                        ),
                    )
                if acknowledgement.get("status") == "SKIPPED":
                    return TcpUploadResult(
                        status="SKIPPED",
                        saved_as=str(acknowledgement.get("saved_as", source.name)),
                        bytes_sent=0,
                        message=str(acknowledgement.get("message", "Tệp đã tồn tại.")),
                    )
                if acknowledgement.get("status") != "OK":
                    raise RuntimeError(
                        str(acknowledgement.get("message", "Server từ chối tệp."))
                    )

                with source.open("rb") as stream:
                    while sent < size:
                        chunk = stream.read(min(CHUNK_SIZE, size - sent))
                        if not chunk:
                            raise OSError("Không thể đọc đủ dữ liệu từ tệp nguồn.")
                        connection.sendall(chunk)
                        sent += len(chunk)
                        if on_progress is not None:
                            elapsed = max(time.monotonic() - started_at, 0.001)
                            progress = 100 if size == 0 else int(sent * 100 / size)
                            on_progress(progress, sent / elapsed)

                if on_waiting_for_ack is not None:
                    on_waiting_for_ack()
                result = _recv_json(connection)
                if result.get("status") == "SKIPPED":
                    return TcpUploadResult(
                        status="SKIPPED",
                        saved_as=str(result.get("saved_as", source.name)),
                        bytes_sent=sent,
                        message=str(result.get("message", "Tệp đã tồn tại.")),
                    )
                if result.get("status") != "SUCCESS":
                    raise RuntimeError(
                        str(result.get("message", "Upload không thành công."))
                    )
                if size == 0 and on_progress is not None:
                    on_progress(100, 0.0)
                return TcpUploadResult(
                    status="SUCCESS",
                    saved_as=str(result.get("saved_as", source.name)),
                    bytes_sent=sent,
                )
        except ConnectionRefusedError as error:
            raise ConnectionError(
                f"Không thể kết nối TCP đến {self.host}:{self.port}."
            ) from error
        except socket.timeout as error:
            raise TimeoutError("Kết nối TCP quá thời gian chờ. Hãy thử lại.") from error

    def check_server(self) -> TcpHealthResult:
        """Xác thực đúng Server UDM mà không tạo tác vụ/file upload."""
        connected = False
        try:
            with socket.create_connection(
                (self.host, self.port), timeout=self.timeout
            ) as connection:
                connected = True
                connection.settimeout(self.timeout)
                _send_json(
                    connection,
                    {
                        "type": "health_check",
                        "protocol": PROTOCOL_NAME,
                        "version": PROTOCOL_VERSION,
                    },
                )
                response = _recv_json(connection)
                if (
                    response.get("status") != "HEALTHY"
                    or response.get("protocol") != PROTOCOL_NAME
                    or response.get("version") != PROTOCOL_VERSION
                ):
                    raise ProtocolMismatchError(
                        "Cổng có phản hồi nhưng không đúng giao thức UDM_10."
                    )
                can_accept = response.get("can_accept_upload")
                active = response.get("active_uploads")
                limit = response.get("upload_limit")
                if (
                    not isinstance(can_accept, bool)
                    or not isinstance(active, int)
                    or not isinstance(limit, int)
                    or active < 0
                    or limit < 1
                    or active > limit
                ):
                    raise ProtocolMismatchError(
                        "Server trả health-check UDM không hợp lệ."
                    )
                return TcpHealthResult(can_accept, active, limit)
        except ProtocolMismatchError:
            raise
        except socket.timeout as error:
            raise TimeoutError("Server không phản hồi trong thời gian cho phép.") from error
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
            if connected:
                raise ProtocolMismatchError(
                    "Cổng có phản hồi nhưng không đúng giao thức UDM_10."
                ) from error
            raise
        except (ConnectionRefusedError, socket.gaierror, OSError) as error:
            if connected:
                raise ProtocolMismatchError(
                    "Cổng đã mở nhưng dịch vụ không phản hồi theo giao thức UDM_10."
                ) from error
            raise ConnectionError(
                f"Không thể kết nối đến {self.host}:{self.port}."
            ) from error

    @staticmethod
    def _validate_source(path: Path, conflict: str) -> None:
        if conflict not in CONFLICT_POLICIES:
            raise ValueError("Chính sách trùng tên không hợp lệ.")
        if not path.is_file():
            raise FileNotFoundError("Không tìm thấy tệp nguồn.")
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError(
                "Định dạng không được hỗ trợ (.txt, .pdf, .jpg, .jpeg, .doc, .docx)."
            )
        if path.stat().st_size > MAX_UPLOAD_SIZE:
            raise ValueError("Dung lượng tệp vượt quá 500 KiB (512.000 byte).")


def _send_json(connection: socket.socket, payload: dict[str, object]) -> None:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if len(raw) > HEADER_MAX:
        raise ValueError("TCP header vượt quá giới hạn cho phép.")
    connection.sendall(len(raw).to_bytes(4, "big") + raw)


def _recv_exact(connection: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = connection.recv(size - len(chunks))
        if not chunk:
            raise ConnectionError("Mất kết nối khi đang nhận phản hồi từ Server.")
        chunks.extend(chunk)
    return bytes(chunks)


def _recv_json(connection: socket.socket) -> dict[str, object]:
    length = int.from_bytes(_recv_exact(connection, 4), "big")
    if length <= 0 or length > HEADER_MAX:
        raise ValueError("Độ dài TCP header không hợp lệ.")
    payload = json.loads(_recv_exact(connection, length).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Phản hồi Server phải là JSON object.")
    return payload
