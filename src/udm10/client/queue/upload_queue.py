"""FIFO upload state machine protected by one re-entrant lock."""

from __future__ import annotations

import threading
from collections.abc import Iterable

from udm10.client.models.upload import ConflictPolicy, UploadItem, UploadStatus


class InvalidStateTransition(ValueError):
    """Raised when a command would violate the upload state machine."""


class UploadQueue:
    """Own ordering, concurrency slots, and immutable upload snapshots."""

    def __init__(self, max_concurrent: int) -> None:
        if max_concurrent <= 0:
            raise ValueError("max_concurrent phải lớn hơn 0.")
        self.max_concurrent = max_concurrent
        self._items: list[UploadItem] = []
        self._lock = threading.RLock()

    def enqueue(self, items: Iterable[UploadItem]) -> tuple[UploadItem, ...]:
        with self._lock:
            existing_ids = {item.id for item in self._items}
            for item in items:
                if item.id in existing_ids:
                    raise ValueError(f"Upload id đã tồn tại: {item.id}")
                if item.status != UploadStatus.WAITING:
                    raise InvalidStateTransition("Item mới phải ở trạng thái waiting.")
                self._items.append(item)
                existing_ids.add(item.id)
            self._normalize_waiting_positions()
            return tuple(self._items)

    def claim_ready(self) -> tuple[UploadItem, ...]:
        with self._lock:
            active = sum(
                item.status == UploadStatus.UPLOADING for item in self._items
            )
            available = max(0, self.max_concurrent - active)
            claimed: list[UploadItem] = []
            if available:
                for index, item in enumerate(self._items):
                    if available == 0:
                        break
                    if item.status != UploadStatus.WAITING:
                        continue
                    if item.duplicate_conflict:
                        # A blocked head remains the FIFO head; later files may
                        # not overtake it while awaiting the user's policy.
                        break
                    uploading = item.updated(
                        status=UploadStatus.UPLOADING,
                        queue_position=None,
                        error_message=None,
                        speed_bytes_per_second=0.0,
                    )
                    self._items[index] = uploading
                    claimed.append(uploading)
                    available -= 1
            self._normalize_waiting_positions()
            return tuple(claimed)

    def snapshot(self) -> tuple[UploadItem, ...]:
        with self._lock:
            return tuple(self._items)

    def finish(
        self,
        upload_id: str,
        status: UploadStatus,
        *,
        error_message: str | None = None,
        stored_name: str | None = None,
    ) -> UploadItem:
        if status not in {
            UploadStatus.COMPLETED,
            UploadStatus.FAILED,
            UploadStatus.SKIPPED,
        }:
            raise InvalidStateTransition("Kết quả upload phải là trạng thái cuối.")
        with self._lock:
            index = self._index_of(upload_id)
            current = self._items[index]
            if current.status != UploadStatus.UPLOADING:
                raise InvalidStateTransition(
                    f"Không thể chuyển {current.status.value} sang {status.value}."
                )
            finished = current.updated(
                name=stored_name or current.name,
                status=status,
                progress=100 if status == UploadStatus.COMPLETED else current.progress,
                speed_bytes_per_second=0.0,
                bytes_sent=(
                    current.size_bytes
                    if status == UploadStatus.COMPLETED
                    else current.bytes_sent
                ),
                error_message=error_message,
                queue_position=None,
            )
            self._items[index] = finished
            self._normalize_waiting_positions()
            return finished

    def defer_conflict(self, upload_id: str) -> UploadItem:
        """Release an active slot while the user chooses a duplicate policy."""
        with self._lock:
            index = self._index_of(upload_id)
            current = self._items[index]
            if current.status != UploadStatus.UPLOADING:
                raise InvalidStateTransition(
                    "Chỉ file uploading mới có thể chờ xử lý trùng tên."
                )
            conflicted = current.updated(
                status=UploadStatus.WAITING,
                duplicate_conflict=True,
                conflict_policy=None,
                progress=0,
                bytes_sent=0,
                speed_bytes_per_second=0.0,
                error_message=None,
            )
            self._items[index] = conflicted
            self._normalize_waiting_positions()
            return self._items[index]

    def record_progress(
        self,
        upload_id: str,
        *,
        bytes_sent: int,
        speed_bytes_per_second: float,
    ) -> UploadItem:
        if bytes_sent < 0 or speed_bytes_per_second < 0:
            raise ValueError("Số byte và tốc độ không được âm.")
        with self._lock:
            index = self._index_of(upload_id)
            current = self._items[index]
            if current.status != UploadStatus.UPLOADING:
                raise InvalidStateTransition(
                    "Chỉ upload đang chạy mới được cập nhật tiến trình."
                )
            sent = min(bytes_sent, current.size_bytes)
            progress = (
                int(sent * 100 / current.size_bytes)
                if current.size_bytes
                else 0
            )
            updated = current.updated(
                bytes_sent=sent,
                progress=progress,
                speed_bytes_per_second=speed_bytes_per_second,
            )
            self._items[index] = updated
            return updated

    def retry(self, upload_id: str) -> UploadItem:
        with self._lock:
            index = self._index_of(upload_id)
            current = self._items[index]
            if current.status != UploadStatus.FAILED:
                raise InvalidStateTransition("Chỉ file failed mới được thử lại.")
            waiting = current.updated(
                status=UploadStatus.WAITING,
                progress=0,
                bytes_sent=0,
                speed_bytes_per_second=0.0,
                error_message=None,
            )
            self._items[index] = waiting
            self._normalize_waiting_positions()
            return self._items[index]

    def skip(self, upload_id: str) -> UploadItem:
        with self._lock:
            index = self._index_of(upload_id)
            current = self._items[index]
            if current.status != UploadStatus.WAITING:
                raise InvalidStateTransition("Chỉ file waiting mới được bỏ qua trực tiếp.")
            skipped = current.updated(
                status=UploadStatus.SKIPPED,
                duplicate_conflict=False,
                conflict_policy=ConflictPolicy.SKIP,
                queue_position=None,
                speed_bytes_per_second=0.0,
            )
            self._items[index] = skipped
            self._normalize_waiting_positions()
            return skipped

    def resolve_conflict(
        self, upload_id: str, policy: ConflictPolicy
    ) -> UploadItem:
        if policy == ConflictPolicy.SKIP:
            return self.skip(upload_id)
        with self._lock:
            index = self._index_of(upload_id)
            current = self._items[index]
            if current.status != UploadStatus.WAITING or not current.duplicate_conflict:
                raise InvalidStateTransition("File không ở trạng thái chờ xử lý trùng tên.")
            resolved = current.updated(
                duplicate_conflict=False,
                conflict_policy=policy,
            )
            self._items[index] = resolved
            self._normalize_waiting_positions()
            return self._items[index]

    def remove(self, upload_id: str) -> None:
        with self._lock:
            index = self._index_of(upload_id)
            if self._items[index].status == UploadStatus.UPLOADING:
                raise InvalidStateTransition("Không thể xóa file đang upload.")
            self._items.pop(index)
            self._normalize_waiting_positions()

    def _index_of(self, upload_id: str) -> int:
        for index, item in enumerate(self._items):
            if item.id == upload_id:
                return index
        raise KeyError(upload_id)

    def _normalize_waiting_positions(self) -> None:
        position = 1
        for index, item in enumerate(self._items):
            if item.status == UploadStatus.WAITING:
                self._items[index] = item.updated(queue_position=position)
                position += 1
            elif item.queue_position is not None:
                self._items[index] = item.updated(queue_position=None)
