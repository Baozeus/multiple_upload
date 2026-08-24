"""History presentation records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class HistoryResult(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    RENAMED = "renamed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    id: str
    name: str
    completed_at: datetime
    size_bytes: int
    result: HistoryResult
