"""Pure-Python upload queue with a strict concurrency limit."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from .limits import (
    ALLOWED_EXTENSIONS,
    MAX_CONCURRENT_UPLOADS,
    MAX_FILES_PER_SELECTION,
    MAX_UPLOAD_SIZE,
)
from .models import UploadItem, UploadStatus


BATCH_LIMIT_REASON = "Mỗi lần chỉ nhận tối đa 6 file."


class UploadQueue:
    def __init__(
        self,
        max_concurrent: int = MAX_CONCURRENT_UPLOADS,
        max_upload_size: int = MAX_UPLOAD_SIZE,
    ) -> None:
        if not 1 <= max_concurrent <= MAX_CONCURRENT_UPLOADS:
            raise ValueError("Giới hạn upload đồng thời phải nằm trong khoảng 1–3.")
        self.max_concurrent = max_concurrent
        if not 0 <= max_upload_size <= MAX_UPLOAD_SIZE:
            raise ValueError(
                "Giới hạn dung lượng phải từ 0 đến 500 MB (524.288.000 byte)."
            )
        self.max_upload_size = max_upload_size
        self.items: OrderedDict[str, UploadItem] = OrderedDict()
        self.rejected: list[tuple[Path, str]] = []

    def add_paths(self, paths: Iterable[str | Path]) -> list[UploadItem]:
        self.rejected = []
        added: list[UploadItem] = []
        for raw_path in paths:
            path = Path(raw_path).resolve()
            if len(added) >= MAX_FILES_PER_SELECTION:
                self.rejected.append((path, BATCH_LIMIT_REASON))
                continue
            if not path.is_file():
                self.rejected.append((path, "Không tìm thấy tệp hoặc đường dẫn không hợp lệ."))
                continue
            if path.suffix.lower() not in ALLOWED_EXTENSIONS:
                self.rejected.append(
                    (path, "Định dạng không được hỗ trợ (.txt, .pdf, .jpg, .jpeg, .doc, .docx).")
                )
                continue
            try:
                size = path.stat().st_size
            except OSError:
                self.rejected.append((path, "Không thể đọc thông tin tệp."))
                continue
            if size > self.max_upload_size:
                self.rejected.append((path, "Dung lượng vượt quá giới hạn cấu hình."))
                continue
            item = UploadItem(path=path)
            self.items[item.id] = item
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
