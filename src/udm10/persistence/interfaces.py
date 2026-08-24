"""Persistence contracts and framework-independent upload history records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class PersistenceError(RuntimeError):
    """Base error safe to report during application bootstrap."""


class PersistenceUnavailable(PersistenceError):
    """The configured backend cannot be reached or initialized."""


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
    started_at: datetime
    completed_at: datetime | None
    relative_path: str | None


@dataclass(frozen=True, slots=True)
class UploadEventRecord:
    id: str
    file_id: str
    status: str
    message: str | None
    created_at: datetime


class HistoryRepository(Protocol):
    def initialize(self) -> None: ...

    def save_batch(self, batch: UploadBatchRecord) -> None: ...

    def save_file(self, file: UploadFileRecord) -> None: ...

    def append_event(self, event: UploadEventRecord) -> None: ...

    def list_batches(self) -> tuple[UploadBatchRecord, ...]: ...

    def list_files(self) -> tuple[UploadFileRecord, ...]: ...

    def list_events(self, file_id: str | None = None) -> tuple[UploadEventRecord, ...]: ...

    def close(self) -> None: ...
