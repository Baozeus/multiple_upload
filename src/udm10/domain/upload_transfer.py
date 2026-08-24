"""Framework-independent values used by the canonical TCP upload flow."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ConflictPolicy(StrEnum):
    OVERWRITE = "overwrite"
    RENAME = "rename"
    SKIP = "skip"


@dataclass(frozen=True, slots=True)
class UploadRequest:
    request_id: str
    batch_id: str
    batch_total: int
    filename: str
    size: int
    conflict: ConflictPolicy | None = None


@dataclass(frozen=True, slots=True)
class StoredFile:
    filename: str
    bytes_received: int
