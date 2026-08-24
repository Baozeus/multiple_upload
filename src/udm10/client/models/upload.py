"""Presentation-safe upload models shared by controllers and widgets."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path


class UploadStatus(StrEnum):
    WAITING = "waiting"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ConflictPolicy(StrEnum):
    OVERWRITE = "overwrite"
    RENAME = "rename"
    SKIP = "skip"


@dataclass(frozen=True, slots=True)
class UploadItem:
    id: str
    name: str
    size_bytes: int
    status: UploadStatus
    progress: int = 0
    speed_bytes_per_second: float = 0.0
    bytes_sent: int = 0
    error_message: str | None = None
    duplicate_conflict: bool = False
    queue_position: int | None = None
    source_path: Path | None = None
    conflict_policy: ConflictPolicy | None = None
    batch_id: str | None = None
    batch_total: int = 1

    def updated(self, **changes: object) -> "UploadItem":
        """Return an updated immutable snapshot for signal-safe delivery."""
        return replace(self, **changes)
