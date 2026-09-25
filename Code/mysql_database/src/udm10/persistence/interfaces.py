"""Stable records shared by persistence adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


class PersistenceError(RuntimeError):
    """A persistence operation failed after the adapter was initialized."""


class PersistenceUnavailable(PersistenceError):
    """The configured persistence backend cannot be used."""


@dataclass(frozen=True, slots=True)
class UploadBatchRecord:
    id: str
    started_at: datetime
    completed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class UploadFileRecord:
    id: str
    batch_id: str
    original_name: str
    stored_name: str | None
    size_bytes: int
    status: str
    duplicate_policy: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    relative_path: str | None


@dataclass(frozen=True, slots=True)
class UploadEventRecord:
    id: str
    file_id: str
    status: str
    message: str | None
    created_at: datetime
