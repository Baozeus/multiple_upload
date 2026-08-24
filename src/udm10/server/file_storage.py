"""Chunked, atomic file storage rooted in one trusted directory."""

from __future__ import annotations

import os
import socket
import threading
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from udm10.domain import ConflictPolicy, StoredFile, UploadRequest
from udm10.server.errors import (
    DestinationBusy,
    DuplicateDetected,
    IncompletePayload,
    StorageFailure,
    TransferTimeout,
)


@dataclass(slots=True)
class UploadStorageSession:
    _storage: "FileStorage"
    request: UploadRequest
    destination: Path
    temporary: Path
    placeholder: bool
    skipped: bool = False
    _closed: bool = False

    def receive_from(self, connection: socket.socket) -> StoredFile:
        received = 0
        try:
            with self.temporary.open("xb") as output:
                remaining = self.request.size
                while remaining:
                    try:
                        chunk = connection.recv(min(self._storage.chunk_size, remaining))
                    except socket.timeout as exc:
                        raise TransferTimeout(
                            "Hết thời gian chờ dữ liệu tệp.", bytes_received=received
                        ) from exc
                    except OSError as exc:
                        raise IncompletePayload(
                            "Kết nối bị ngắt khi đang nhận tệp.", bytes_received=received
                        ) from exc
                    if not chunk:
                        raise IncompletePayload(
                            "Payload kết thúc trước dung lượng đã khai báo.",
                            bytes_received=received,
                        )
                    try:
                        output.write(chunk)
                    except OSError as exc:
                        raise StorageFailure(
                            "Không thể ghi dữ liệu tệp xuống ổ đĩa.",
                            bytes_received=received,
                        ) from exc
                    received += len(chunk)
                    remaining -= len(chunk)
                output.flush()
                os.fsync(output.fileno())
            os.replace(self.temporary, self.destination)
            self._closed = True
            self._storage._release(self.destination)
            return StoredFile(self.destination.name, received)
        except (IncompletePayload, TransferTimeout, StorageFailure):
            self.abort()
            raise
        except OSError as exc:
            self.abort()
            raise StorageFailure(
                "Không thể hoàn tất lưu tệp.", bytes_received=received
            ) from exc

    def abort(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.temporary.unlink(missing_ok=True)
        if self.placeholder:
            self.destination.unlink(missing_ok=True)
        self._storage._release(self.destination)


class FileStorage:
    """Reserve a safe destination and stream a payload without buffering it all."""

    def __init__(self, root: Path, *, chunk_size: int = 64 * 1024) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size phải lớn hơn 0.")
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.chunk_size = chunk_size
        self._lock = threading.Lock()
        self._reserved: set[Path] = set()

    def begin(self, request: UploadRequest) -> UploadStorageSession:
        try:
            with self._lock:
                destination, placeholder, skipped = self._reserve_destination(request)
                temporary = self.root / f".{destination.name}.{uuid4().hex}.part"
                return UploadStorageSession(
                    self, request, destination, temporary, placeholder, skipped
                )
        except StorageFailure:
            raise
        except OSError as exc:
            raise StorageFailure("Không thể chuẩn bị vị trí lưu tệp.") from exc

    def _reserve_destination(self, request: UploadRequest) -> tuple[Path, bool, bool]:
        requested = self._contained_path(request.filename)
        exists = requested.exists() or requested in self._reserved
        if request.conflict is None and exists:
            raise DuplicateDetected(requested.name)
        if request.conflict == ConflictPolicy.SKIP and exists:
            return requested, False, True
        if request.conflict == ConflictPolicy.RENAME and exists:
            requested = self._next_available_name(requested)

        if request.conflict == ConflictPolicy.OVERWRITE and requested in self._reserved:
            raise DestinationBusy("Tệp đích đang được tải lên. Hãy thử lại sau.")

        placeholder = request.conflict != ConflictPolicy.OVERWRITE
        if placeholder:
            try:
                requested.touch(exist_ok=False)
            except FileExistsError:
                if request.conflict == ConflictPolicy.RENAME:
                    requested = self._next_available_name(requested)
                    requested.touch(exist_ok=False)
                else:
                    raise DuplicateDetected(requested.name)
        self._reserved.add(requested)
        return requested, placeholder, False

    def _next_available_name(self, requested: Path) -> Path:
        stem, suffix = requested.stem, requested.suffix
        index = 1
        while True:
            candidate = self._contained_path(f"{stem}_{index}{suffix}")
            if not candidate.exists() and candidate not in self._reserved:
                return candidate
            index += 1

    def _contained_path(self, filename: str) -> Path:
        candidate = (self.root / filename).resolve()
        if candidate.parent != self.root:
            raise StorageFailure("Đường dẫn lưu tệp vượt ngoài thư mục upload.")
        return candidate

    def _release(self, destination: Path) -> None:
        with self._lock:
            self._reserved.discard(destination)
