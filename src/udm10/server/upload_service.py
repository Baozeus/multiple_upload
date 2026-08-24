"""Deep upload module coordinating messages, validation, and storage."""

from __future__ import annotations

import socket
from datetime import UTC, datetime
from collections.abc import Callable, Mapping
from typing import Any
from uuid import uuid4

from udm10.domain import ConflictPolicy, UploadRequest
from udm10.persistence import (
    HistoryRepository,
    UploadBatchRecord,
    UploadEventRecord,
    UploadFileRecord,
)

from udm10.protocol import (
    ProtocolError,
    parse_upload_start,
    upload_completed,
    upload_conflict,
    upload_failed,
    upload_ready,
    upload_skipped,
)
from udm10.server.errors import DuplicateDetected, UploadError
from udm10.server.file_storage import FileStorage
from udm10.server.validation import UploadValidator


class UploadService:
    """Process one upload behind a single connection-facing interface."""

    def __init__(
        self,
        validator: UploadValidator,
        storage: FileStorage,
        *,
        history_repository: HistoryRepository | None = None,
    ) -> None:
        self._validator = validator
        self._storage = storage
        self._history = history_repository

    def process(
        self,
        message: Mapping[str, Any],
        connection: socket.socket,
        announce: Callable[[Mapping[str, Any]], None],
    ) -> dict[str, Any]:
        request_id = message.get("request_id")
        safe_request_id = request_id if isinstance(request_id, str) else None
        request: UploadRequest | None = None
        started_at = datetime.now(UTC)
        try:
            request = self._validator.validate(parse_upload_start(message))
            started_at = self._existing_started_at(request.request_id) or started_at
            self._record(
                request,
                status="uploading",
                started_at=started_at,
                original_name=_original_name(message, request.filename),
            )
            session = self._storage.begin(request)
            if session.skipped:
                completed_at = datetime.now(UTC)
                self._record(
                    request,
                    status="skipped",
                    started_at=started_at,
                    completed_at=completed_at,
                    original_name=_original_name(message, request.filename),
                    stored_name=session.destination.name,
                )
                return upload_skipped(request.request_id, session.destination.name)
            try:
                announce(upload_ready(request.request_id))
            except (ConnectionError, OSError):
                session.abort()
                raise
            stored = session.receive_from(connection)
            completed_at = datetime.now(UTC)
            self._record(
                request,
                status="completed",
                started_at=started_at,
                completed_at=completed_at,
                original_name=_original_name(message, request.filename),
                stored_name=stored.filename,
                relative_path=stored.filename,
            )
            return upload_completed(request.request_id, stored)
        except DuplicateDetected as exc:
            if request is not None:
                self._record(
                    request,
                    status="waiting",
                    started_at=started_at,
                    original_name=_original_name(message, request.filename),
                    error_message="Tệp đã tồn tại trên máy chủ.",
                )
            return upload_conflict(safe_request_id or "", exc.filename)
        except ProtocolError as exc:
            return upload_failed(
                safe_request_id, code="invalid_metadata", message=str(exc)
            )
        except UploadError as exc:
            if request is not None:
                self._record(
                    request,
                    status="failed",
                    started_at=started_at,
                    completed_at=datetime.now(UTC),
                    original_name=_original_name(message, request.filename),
                    error_message=str(exc),
                )
            return upload_failed(
                safe_request_id,
                code=exc.code,
                message=str(exc),
                bytes_received=exc.bytes_received,
            )

    def record_skip(self, message: Mapping[str, Any]) -> dict[str, Any]:
        """Persist an explicit user skip without opening a binary transfer."""
        request_id = message.get("request_id")
        safe_request_id = request_id if isinstance(request_id, str) else None
        try:
            upload_message = dict(message)
            upload_message["type"] = "upload.start"
            upload_message["conflict"] = ConflictPolicy.SKIP.value
            request = self._validator.validate(parse_upload_start(upload_message))
            started_at = self._existing_started_at(request.request_id) or datetime.now(UTC)
            self._record(
                request,
                status="skipped",
                started_at=started_at,
                completed_at=datetime.now(UTC),
                original_name=_original_name(message, request.filename),
                stored_name=request.filename,
            )
            return upload_skipped(request.request_id, request.filename)
        except ProtocolError as exc:
            return upload_failed(
                safe_request_id, code="invalid_metadata", message=str(exc)
            )
        except UploadError as exc:
            return upload_failed(safe_request_id, code=exc.code, message=str(exc))

    def _existing_started_at(self, request_id: str) -> datetime | None:
        if self._history is None:
            return None
        return next(
            (
                record.started_at
                for record in self._history.list_files()
                if record.id == request_id
            ),
            None,
        )

    def _record(
        self,
        request: UploadRequest,
        *,
        status: str,
        started_at: datetime,
        original_name: str,
        completed_at: datetime | None = None,
        stored_name: str | None = None,
        error_message: str | None = None,
        relative_path: str | None = None,
    ) -> None:
        if self._history is None:
            return
        self._history.save_batch(
            UploadBatchRecord(
                id=request.batch_id,
                started_at=started_at,
                completed_at=None,
            )
        )
        self._history.save_file(
            UploadFileRecord(
                id=request.request_id,
                batch_id=request.batch_id,
                original_name=original_name,
                stored_name=stored_name,
                size_bytes=request.size,
                status=status,
                duplicate_policy=(
                    request.conflict.value if request.conflict is not None else None
                ),
                error_message=error_message,
                started_at=started_at,
                completed_at=completed_at,
                relative_path=relative_path,
            )
        )
        self._history.append_event(
            UploadEventRecord(
                id=uuid4().hex,
                file_id=request.request_id,
                status=status,
                message=error_message,
                created_at=completed_at or datetime.now(UTC),
            )
        )
        if status in {"completed", "failed", "skipped"}:
            batch_files = tuple(
                file
                for file in self._history.list_files()
                if file.batch_id == request.batch_id
            )
            if len(batch_files) >= request.batch_total and all(
                file.status in {"completed", "failed", "skipped"}
                for file in batch_files
            ):
                completion_times = tuple(
                    file.completed_at
                    for file in batch_files
                    if file.completed_at is not None
                )
                self._history.save_batch(
                    UploadBatchRecord(
                        id=request.batch_id,
                        started_at=min(file.started_at for file in batch_files),
                        completed_at=max(completion_times),
                    )
                )


def _original_name(message: Mapping[str, Any], fallback: str) -> str:
    value = message.get("filename")
    return value if isinstance(value, str) else fallback
