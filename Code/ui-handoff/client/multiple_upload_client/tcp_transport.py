"""Pure-Python TCP Adapter for the existing UDM_10 upload protocol."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import socket
import time
from typing import Callable


HEADER_MAX = 64 * 1024
CHUNK_SIZE = 64 * 1024
DEFAULT_TIMEOUT = 10.0
MAX_UPLOAD_SIZE = 10 * 1024 * 1024 * 1024
ALLOWED_EXTENSIONS = frozenset({".txt", ".pdf", ".jpg", ".jpeg", ".doc", ".docx"})
CONFLICT_POLICIES = frozenset({"rename", "overwrite", "skip"})


ProgressCallback = Callable[[int, float], None]


@dataclass(frozen=True, slots=True)
class TcpUploadResult:
    status: str
    saved_as: str
    bytes_sent: int
    message: str = ""


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
            raise ValueError("Dung lượng tệp vượt quá giới hạn 10 GB.")


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
