"""Domain models shared by the queue, uploader and user interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from uuid import uuid4


class UploadStatus(str, Enum):
    WAITING = "Chờ"
    UPLOADING = "Đang tải"
    COMPLETED = "Hoàn tất"
    ERROR = "Lỗi"


@dataclass(slots=True)
class UploadItem:
    path: Path
    id: str = field(default_factory=lambda: uuid4().hex)
    status: UploadStatus = UploadStatus.WAITING
    progress: int = 0
    speed: str = "—"
    detail: str = "Đang chờ đến lượt"
    conflict_pending: bool = False
    conflict_policy: str | None = None
    conflict_result: str = "Không"
    used_mock_fallback: bool = False
    added_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def size(self) -> int:
        try:
            return self.path.stat().st_size
        except OSError:
            return 0

    @property
    def extension(self) -> str:
        return self.path.suffix.lstrip(".").lower() or "file"

    def reset_for_retry(self) -> None:
        self.status = UploadStatus.WAITING
        self.progress = 0
        self.speed = "—"
        self.detail = "Đang chờ đến lượt"
        self.conflict_pending = False
        self.started_at = None
        self.finished_at = None

    @property
    def elapsed_text(self) -> str:
        if self.started_at is None:
            return "—"
        end = self.finished_at or datetime.now().astimezone()
        seconds = max(0, int((end - self.started_at).total_seconds()))
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_file_size(size: int) -> str:
    units = ("byte", "KB", "MB", "GB", "TB")
    value = float(size)
    unit = units[0]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            break
        value /= 1024
    precision = 0 if unit == "byte" else 1
    return f"{value:.{precision}f} {unit}".replace(".", ",")
