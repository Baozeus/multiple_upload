"""Thread-safe JSON history repository with atomic file replacement."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from udm10.persistence.interfaces import (
    PersistenceError,
    UploadBatchRecord,
    UploadEventRecord,
    UploadFileRecord,
)

_EMPTY_DOCUMENT: dict[str, Any] = {
    "version": 1,
    "upload_batches": [],
    "upload_files": [],
    "upload_events": [],
}


class JsonHistoryRepository:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self._lock = threading.RLock()

    def initialize(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if not self.path.exists():
                self._write(dict(_EMPTY_DOCUMENT))
            self._read()

    def save_batch(self, batch: UploadBatchRecord) -> None:
        with self._lock:
            document = self._read()
            rows = document["upload_batches"]
            for index, current in enumerate(rows):
                if current.get("id") != batch.id:
                    continue
                existing = _batch_from_dict(current)
                merged = UploadBatchRecord(
                    id=batch.id,
                    started_at=min(existing.started_at, batch.started_at),
                    completed_at=batch.completed_at or existing.completed_at,
                )
                rows[index] = _batch_to_dict(merged)
                break
            else:
                rows.append(_batch_to_dict(batch))
            self._write(document)

    def save_file(self, file: UploadFileRecord) -> None:
        self._upsert("upload_files", _file_to_dict(file))

    def append_event(self, event: UploadEventRecord) -> None:
        self._upsert("upload_events", _event_to_dict(event))

    def list_batches(self) -> tuple[UploadBatchRecord, ...]:
        with self._lock:
            rows = self._read()["upload_batches"]
            return tuple(_batch_from_dict(row) for row in rows)

    def list_files(self) -> tuple[UploadFileRecord, ...]:
        with self._lock:
            rows = self._read()["upload_files"]
            records = tuple(_file_from_dict(row) for row in rows)
            return tuple(
                sorted(
                    records,
                    key=lambda record: record.completed_at or record.started_at,
                    reverse=True,
                )
            )

    def list_events(
        self, file_id: str | None = None
    ) -> tuple[UploadEventRecord, ...]:
        with self._lock:
            rows = self._read()["upload_events"]
            events = tuple(_event_from_dict(row) for row in rows)
            if file_id is not None:
                events = tuple(event for event in events if event.file_id == file_id)
            return tuple(sorted(events, key=lambda event: event.created_at))

    def close(self) -> None:
        return None

    def _upsert(self, collection: str, row: dict[str, Any]) -> None:
        with self._lock:
            document = self._read()
            rows = document[collection]
            for index, current in enumerate(rows):
                if current.get("id") == row["id"]:
                    rows[index] = row
                    break
            else:
                rows.append(row)
            self._write(document)

    def _read(self) -> dict[str, Any]:
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PersistenceError(
                f"Không thể đọc lịch sử JSON: {self.path}"
            ) from exc
        if not isinstance(document, dict) or any(
            not isinstance(document.get(key), list)
            for key in ("upload_batches", "upload_files", "upload_events")
        ):
            raise PersistenceError("Cấu trúc file lịch sử JSON không hợp lệ.")
        return document

    def _write(self, document: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as output:
                json.dump(document, output, ensure_ascii=False, indent=2)
                output.write("\n")
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise PersistenceError(
                f"Không thể ghi lịch sử JSON: {self.path}"
            ) from exc


def _batch_to_dict(record: UploadBatchRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "started_at": record.started_at.isoformat(),
        "completed_at": _optional_datetime(record.completed_at),
    }


def _batch_from_dict(row: dict[str, Any]) -> UploadBatchRecord:
    return UploadBatchRecord(
        id=str(row["id"]),
        started_at=datetime.fromisoformat(row["started_at"]),
        completed_at=_parse_optional_datetime(row.get("completed_at")),
    )


def _file_to_dict(record: UploadFileRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "batch_id": record.batch_id,
        "original_name": record.original_name,
        "stored_name": record.stored_name,
        "size_bytes": record.size_bytes,
        "status": record.status,
        "duplicate_policy": record.duplicate_policy,
        "error_message": record.error_message,
        "started_at": record.started_at.isoformat(),
        "completed_at": _optional_datetime(record.completed_at),
        "relative_path": record.relative_path,
    }


def _file_from_dict(row: dict[str, Any]) -> UploadFileRecord:
    return UploadFileRecord(
        id=str(row["id"]),
        batch_id=str(row["batch_id"]),
        original_name=str(row["original_name"]),
        stored_name=_optional_string(row.get("stored_name")),
        size_bytes=int(row["size_bytes"]),
        status=str(row["status"]),
        duplicate_policy=_optional_string(row.get("duplicate_policy")),
        error_message=_optional_string(row.get("error_message")),
        started_at=datetime.fromisoformat(row["started_at"]),
        completed_at=_parse_optional_datetime(row.get("completed_at")),
        relative_path=_optional_string(row.get("relative_path")),
    )


def _event_to_dict(record: UploadEventRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "file_id": record.file_id,
        "status": record.status,
        "message": record.message,
        "created_at": record.created_at.isoformat(),
    }


def _event_from_dict(row: dict[str, Any]) -> UploadEventRecord:
    return UploadEventRecord(
        id=str(row["id"]),
        file_id=str(row["file_id"]),
        status=str(row["status"]),
        message=_optional_string(row.get("message")),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _optional_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _parse_optional_datetime(value: Any) -> datetime | None:
    return datetime.fromisoformat(value) if isinstance(value, str) else None


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None
