"""Qt adapter joining the thread-safe queue to blocking TCP upload workers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal, Slot

from udm10.client.models.history import HistoryEntry, HistoryResult
from udm10.client.models.upload import ConflictPolicy, UploadItem, UploadStatus
from udm10.client.transports import (
    ConflictNotice,
    TcpUploadError,
    TransferProgress,
    UploadOutcome,
)
from udm10.client.queue import InvalidStateTransition, UploadQueue


class UploadClient(Protocol):
    def upload(
        self,
        source: Path,
        *,
        request_id: str,
        batch_id: str | None,
        batch_total: int,
        conflict: ConflictPolicy | None,
        on_progress,
    ) -> UploadOutcome | ConflictNotice: ...

    def health_check(self) -> bool: ...

    def load_history(self) -> tuple[HistoryEntry, ...]: ...

    def record_skip(
        self,
        *,
        request_id: str,
        batch_id: str,
        batch_total: int,
        filename: str,
        size_bytes: int,
    ) -> None: ...


class TcpUploadProvider(QObject):
    """Present a signal-based UI interface while all socket I/O stays off-thread."""

    uploads_changed = Signal(object)
    history_changed = Signal(object)
    history_loading_changed = Signal(bool)
    history_error = Signal(str)
    connection_changed = Signal(bool)
    duplicate_detected = Signal(str)

    def __init__(
        self,
        *,
        max_concurrent: int,
        uploader: UploadClient,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._queue = UploadQueue(max_concurrent)
        self._uploader = uploader
        self._history: list[HistoryEntry] = []
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(max_concurrent)
        self._health_pool = QThreadPool(self)
        self._health_pool.setMaxThreadCount(1)
        self._history_pool = QThreadPool(self)
        self._history_pool.setMaxThreadCount(1)
        self._workers: dict[str, _UploadRunnable] = {}
        self._health_worker: _HealthRunnable | None = None
        self._history_worker: _HistoryRunnable | None = None
        self._skip_workers: dict[str, _SkipRunnable] = {}

    def current_uploads(self) -> tuple[UploadItem, ...]:
        return self._queue.snapshot()

    def current_history(self) -> tuple[HistoryEntry, ...]:
        return tuple(self._history)

    @Slot(object)
    def add_files(self, paths: list[Path]) -> None:
        batch_id = uuid4().hex
        items: list[UploadItem] = []
        for path in paths:
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            items.append(
                UploadItem(
                    id=uuid4().hex,
                    name=path.name,
                    size_bytes=size,
                    status=UploadStatus.WAITING,
                    source_path=path,
                    batch_id=batch_id,
                    batch_total=len(paths),
                )
            )
        if items:
            self._queue.enqueue(items)
            self._schedule()

    @Slot(str)
    def retry_upload(self, upload_id: str) -> None:
        try:
            self._queue.retry(upload_id)
        except (KeyError, InvalidStateTransition):
            return
        self._schedule()

    @Slot(str)
    def remove_upload(self, upload_id: str) -> None:
        try:
            self._queue.remove(upload_id)
        except (KeyError, InvalidStateTransition):
            return
        self.uploads_changed.emit(self._queue.snapshot())

    def resolve_duplicate(
        self, upload_id: str, policy: ConflictPolicy, apply_to_remaining: bool
    ) -> None:
        targets = [upload_id]
        if apply_to_remaining:
            targets.extend(
                item.id
                for item in self._queue.snapshot()
                if item.duplicate_conflict and item.id != upload_id
            )
        history_changed = False
        for target in targets:
            try:
                item = self._queue.resolve_conflict(target, policy)
            except (KeyError, InvalidStateTransition):
                continue
            if item.status == UploadStatus.SKIPPED:
                self._append_history(item, HistoryResult.SKIPPED)
                history_changed = True
                worker = _SkipRunnable(item, self._uploader)
                worker.signals.finished.connect(
                    self._on_skip_recorded, Qt.ConnectionType.QueuedConnection
                )
                self._skip_workers[item.id] = worker
                self._pool.start(worker)
        if history_changed:
            self.history_changed.emit(self.current_history())
        self._schedule()

    def refresh_history(self) -> None:
        if self._history_worker is not None:
            return
        self.history_loading_changed.emit(True)
        worker = _HistoryRunnable(self._uploader)
        worker.signals.finished.connect(
            self._on_history_finished, Qt.ConnectionType.QueuedConnection
        )
        self._history_worker = worker
        self._history_pool.start(worker)

    def retry_connection(self) -> None:
        if self._health_worker is not None:
            return
        worker = _HealthRunnable(self._uploader)
        worker.signals.finished.connect(
            self._on_health_finished, Qt.ConnectionType.QueuedConnection
        )
        self._health_worker = worker
        self._health_pool.start(worker)

    def shutdown(self, wait_msecs: int = 3000) -> bool:
        uploads_done = self._pool.waitForDone(wait_msecs)
        health_done = self._health_pool.waitForDone(wait_msecs)
        history_done = self._history_pool.waitForDone(wait_msecs)
        return uploads_done and health_done and history_done

    def _schedule(self) -> None:
        claimed = self._queue.claim_ready()
        self.uploads_changed.emit(self._queue.snapshot())
        for item in claimed:
            if item.source_path is None:
                self._queue.finish(
                    item.id,
                    UploadStatus.FAILED,
                    error_message="Không tìm thấy đường dẫn tệp nguồn.",
                )
                continue
            worker = _UploadRunnable(item, self._uploader)
            worker.signals.progress.connect(
                self._on_progress, Qt.ConnectionType.QueuedConnection
            )
            worker.signals.finished.connect(
                self._on_upload_finished, Qt.ConnectionType.QueuedConnection
            )
            self._workers[item.id] = worker
            self._pool.start(worker)

    @Slot(str, object)
    def _on_progress(self, upload_id: str, progress: TransferProgress) -> None:
        try:
            self._queue.record_progress(
                upload_id,
                bytes_sent=progress.bytes_sent,
                speed_bytes_per_second=progress.speed_bytes_per_second,
            )
        except (KeyError, InvalidStateTransition):
            return
        self.uploads_changed.emit(self._queue.snapshot())

    @Slot(str, object)
    def _on_upload_finished(self, upload_id: str, result: "_WorkerResult") -> None:
        self._workers.pop(upload_id, None)
        try:
            current = next(item for item in self._queue.snapshot() if item.id == upload_id)
        except StopIteration:
            return

        if isinstance(result.outcome, ConflictNotice):
            try:
                self._queue.defer_conflict(upload_id)
            except (KeyError, InvalidStateTransition):
                return
            self.uploads_changed.emit(self._queue.snapshot())
            self.connection_changed.emit(True)
            self.duplicate_detected.emit(upload_id)
            self._schedule()
            return

        if result.outcome is not None:
            outcome = result.outcome
            finished = self._queue.finish(
                upload_id,
                outcome.status,
                error_message=outcome.error_message,
                stored_name=outcome.stored_name,
            )
            history_result = {
                UploadStatus.COMPLETED: (
                    HistoryResult.RENAMED
                    if outcome.stored_name and outcome.stored_name != current.name
                    else HistoryResult.SUCCESS
                ),
                UploadStatus.FAILED: HistoryResult.FAILED,
                UploadStatus.SKIPPED: HistoryResult.SKIPPED,
            }[outcome.status]
            self._append_history(finished, history_result)
            self.connection_changed.emit(True)
        else:
            error = result.error
            message = str(error) if error is not None else "Upload thất bại."
            finished = self._queue.finish(
                upload_id, UploadStatus.FAILED, error_message=message
            )
            self._append_history(finished, HistoryResult.FAILED)
            if isinstance(error, TcpUploadError) and error.code in {
                "connection_error",
                "connection_timeout",
            }:
                self.connection_changed.emit(False)

        self.history_changed.emit(self.current_history())
        self._schedule()

    @Slot(bool)
    def _on_health_finished(self, online: bool) -> None:
        self._health_worker = None
        self.connection_changed.emit(online)

    def _append_history(self, item: UploadItem, result: HistoryResult) -> None:
        entry = HistoryEntry(
            id=item.id,
            name=item.name,
            completed_at=datetime.now(),
            size_bytes=item.size_bytes,
            result=result,
        )
        for index, current in enumerate(self._history):
            if current.id == item.id:
                self._history[index] = entry
                break
        else:
            self._history.insert(
                0,
                entry,
            )

    @Slot(object, object)
    def _on_history_finished(
        self, entries: tuple[HistoryEntry, ...] | None, error: Exception | None
    ) -> None:
        self._history_worker = None
        self.history_loading_changed.emit(False)
        if error is not None:
            self.history_error.emit(str(error))
            return
        self._history = list(entries or ())
        self.history_changed.emit(self.current_history())

    @Slot(str, object)
    def _on_skip_recorded(self, upload_id: str, error: Exception | None) -> None:
        self._skip_workers.pop(upload_id, None)
        if error is not None:
            self.history_error.emit(str(error))


class _UploadSignals(QObject):
    progress = Signal(str, object)
    finished = Signal(str, object)


class _WorkerResult:
    __slots__ = ("outcome", "error")

    def __init__(
        self,
        outcome: UploadOutcome | ConflictNotice | None = None,
        error: Exception | None = None,
    ) -> None:
        self.outcome = outcome
        self.error = error


class _UploadRunnable(QRunnable):
    def __init__(self, item: UploadItem, uploader: UploadClient) -> None:
        super().__init__()
        self.item = item
        self.uploader = uploader
        self.signals = _UploadSignals()

    def run(self) -> None:
        try:
            outcome = self.uploader.upload(
                self.item.source_path,
                request_id=self.item.id,
                batch_id=self.item.batch_id,
                batch_total=self.item.batch_total,
                conflict=self.item.conflict_policy,
                on_progress=lambda progress: self.signals.progress.emit(
                    self.item.id, progress
                ),
            )
        except Exception as exc:  # Worker must isolate every per-file failure.
            result = _WorkerResult(error=exc)
        else:
            result = _WorkerResult(outcome=outcome)
        self.signals.finished.emit(self.item.id, result)


class _HealthSignals(QObject):
    finished = Signal(bool)


class _HealthRunnable(QRunnable):
    def __init__(self, uploader: UploadClient) -> None:
        super().__init__()
        self.uploader = uploader
        self.signals = _HealthSignals()

    def run(self) -> None:
        self.signals.finished.emit(self.uploader.health_check())


class _HistorySignals(QObject):
    finished = Signal(object, object)


class _HistoryRunnable(QRunnable):
    def __init__(self, uploader: UploadClient) -> None:
        super().__init__()
        self.uploader = uploader
        self.signals = _HistorySignals()

    def run(self) -> None:
        try:
            entries = self.uploader.load_history()
        except Exception as exc:
            self.signals.finished.emit(None, exc)
        else:
            self.signals.finished.emit(entries, None)


class _SkipSignals(QObject):
    finished = Signal(str, object)


class _SkipRunnable(QRunnable):
    def __init__(self, item: UploadItem, uploader: UploadClient) -> None:
        super().__init__()
        self.item = item
        self.uploader = uploader
        self.signals = _SkipSignals()

    def run(self) -> None:
        error: Exception | None = None
        try:
            self.uploader.record_skip(
                request_id=self.item.id,
                batch_id=self.item.batch_id or self.item.id,
                batch_total=self.item.batch_total,
                filename=self.item.name,
                size_bytes=self.item.size_bytes,
            )
        except Exception as exc:
            error = exc
        self.signals.finished.emit(self.item.id, error)
