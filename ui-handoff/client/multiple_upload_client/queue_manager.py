"""Pure-Python upload queue with a strict concurrency limit."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from .models import UploadItem, UploadStatus


MAX_CONCURRENT_UPLOADS = 6


class UploadQueue:
    def __init__(self, max_concurrent: int = MAX_CONCURRENT_UPLOADS) -> None:
        if not 1 <= max_concurrent <= MAX_CONCURRENT_UPLOADS:
            raise ValueError("Giới hạn upload đồng thời phải nằm trong khoảng 1–6.")
        self.max_concurrent = max_concurrent
        self.items: OrderedDict[str, UploadItem] = OrderedDict()

    def add_paths(self, paths: Iterable[str | Path]) -> list[UploadItem]:
        existing = {item.path.resolve() for item in self.items.values()}
        added: list[UploadItem] = []
        for raw_path in paths:
            path = Path(raw_path).resolve()
            if path in existing or not path.is_file():
                continue
            item = UploadItem(path=path)
            self.items[item.id] = item
            existing.add(path)
            added.append(item)
        return added

    def take_next(self) -> list[UploadItem]:
        active_count = sum(
            item.status is UploadStatus.UPLOADING for item in self.items.values()
        )
        available_slots = max(0, self.max_concurrent - active_count)
        selected: list[UploadItem] = []
        for item in self.items.values():
            if available_slots == 0:
                break
            if item.status is UploadStatus.WAITING and not item.conflict_pending:
                item.status = UploadStatus.UPLOADING
                item.started_at = datetime.now().astimezone()
                item.detail = "Đang gửi dữ liệu"
                selected.append(item)
                available_slots -= 1
        return selected

    def remove(self, item_id: str) -> bool:
        item = self.items.get(item_id)
        if item is None or item.status is UploadStatus.UPLOADING:
            return False
        del self.items[item_id]
        return True

    def clear_removable(self) -> int:
        removable = [
            item_id
            for item_id, item in self.items.items()
            if item.status is not UploadStatus.UPLOADING
        ]
        for item_id in removable:
            del self.items[item_id]
        return len(removable)

    def stats(self) -> dict[str, int]:
        counts = {status.value: 0 for status in UploadStatus}
        for item in self.items.values():
            counts[item.status.value] += 1
        return {"Tổng": len(self.items), **counts}
