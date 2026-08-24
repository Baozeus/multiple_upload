from __future__ import annotations

import threading
from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtCore import QTimer

from udm10.client.models.history import HistoryResult
from udm10.client.models.history import HistoryEntry
from udm10.client.models.upload import ConflictPolicy, UploadStatus
from udm10.client.models.tcp_provider import TcpUploadProvider
from udm10.client.transports import (
    ConflictNotice,
    TcpUploadError,
    TransferProgress,
    UploadOutcome,
)


class ControlledUploader:
    def __init__(self) -> None:
        self.started: list[str] = []
        self.batch_ids: list[str | None] = []
        self.batch_totals: list[int | None] = []
        self._lock = threading.Lock()
        self._release: dict[str, threading.Event] = {}

    def upload(
        self,
        source,
        *,
        request_id,
        batch_id=None,
        batch_total=None,
        conflict,
        on_progress,
    ):
        event = threading.Event()
        with self._lock:
            self.started.append(request_id)
            self.batch_ids.append(batch_id)
            self.batch_totals.append(batch_total)
            self._release[request_id] = event
        on_progress(TransferProgress(50, 100, 50, 125.0))
        if not event.wait(3):
            raise RuntimeError("Test worker không được giải phóng.")
        on_progress(TransferProgress(100, 100, 100, 250.0))
        return UploadOutcome(UploadStatus.COMPLETED, source.name, 100)

    def release(self, request_id: str) -> None:
        self._release[request_id].set()

    def health_check(self) -> bool:
        return True


def test_provider_limits_workers_starts_fifo_and_keeps_event_loop_responsive(
    qtbot, tmp_path: Path
) -> None:
    paths = []
    for index in range(3):
        path = tmp_path / f"file-{index}.bin"
        path.write_bytes(b"x" * 100)
        paths.append(path)

    uploader = ControlledUploader()
    provider = TcpUploadProvider(max_concurrent=2, uploader=uploader)
    provider.add_files(paths)
    qtbot.waitUntil(lambda: len(uploader.started) == 2)

    snapshot = provider.current_uploads()
    assert [item.status for item in snapshot] == [
        UploadStatus.UPLOADING,
        UploadStatus.UPLOADING,
        UploadStatus.WAITING,
    ]
    assert [snapshot[index].name for index in range(2)] == [
        "file-0.bin",
        "file-1.bin",
    ]
    assert len(set(uploader.batch_ids)) == 1
    assert uploader.batch_ids[0]
    assert uploader.batch_totals == [3, 3]

    event_loop_ticked: list[bool] = []
    QTimer.singleShot(0, lambda: event_loop_ticked.append(True))
    qtbot.waitUntil(lambda: bool(event_loop_ticked))

    uploader.release(snapshot[0].id)
    qtbot.waitUntil(lambda: len(uploader.started) == 3)
    assert provider.current_uploads()[2].status == UploadStatus.UPLOADING

    for request_id in tuple(uploader.started):
        if request_id != snapshot[0].id:
            uploader.release(request_id)
    qtbot.waitUntil(
        lambda: all(
            item.status == UploadStatus.COMPLETED
            for item in provider.current_uploads()
        )
    )
    provider.shutdown()


class FailFirstUploader:
    def upload(self, source, *, request_id, batch_id=None, batch_total=1, conflict, on_progress):
        if source.name == "bad.bin":
            raise TcpUploadError("connection_error", "Mất kết nối thử nghiệm")
        on_progress(TransferProgress(100, 100, 100, 300.0))
        return UploadOutcome(UploadStatus.COMPLETED, source.name, 100)

    def health_check(self) -> bool:
        return True


def test_tc20_network_failure_only_fails_related_file_and_queue_continues(
    qtbot, tmp_path: Path
) -> None:
    bad = tmp_path / "bad.bin"
    good = tmp_path / "good.bin"
    bad.write_bytes(b"x" * 100)
    good.write_bytes(b"y" * 100)
    provider = TcpUploadProvider(max_concurrent=1, uploader=FailFirstUploader())

    provider.add_files([bad, good])
    qtbot.waitUntil(
        lambda: [item.status for item in provider.current_uploads()]
        == [UploadStatus.FAILED, UploadStatus.COMPLETED]
    )

    first, second = provider.current_uploads()
    assert "Mất kết nối" in (first.error_message or "")
    assert second.progress == 100
    provider.shutdown()


class ConflictOnceUploader:
    def __init__(self) -> None:
        self.calls: list[ConflictPolicy | None] = []

    def upload(self, source, *, request_id, batch_id=None, batch_total=1, conflict, on_progress):
        self.calls.append(conflict)
        if conflict is None:
            return ConflictNotice(source.name)
        on_progress(TransferProgress(100, 100, 100, 300.0))
        return UploadOutcome(UploadStatus.COMPLETED, source.name, 100)

    def health_check(self) -> bool:
        return True


def test_tc21_provider_waits_for_user_choice_then_retries_with_that_policy(
    qtbot, tmp_path: Path
) -> None:
    source = tmp_path / "trùng Unicode.txt"
    source.write_bytes(b"x" * 100)
    uploader = ConflictOnceUploader()
    provider = TcpUploadProvider(max_concurrent=1, uploader=uploader)

    with qtbot.waitSignal(provider.duplicate_detected) as blocker:
        provider.add_files([source])

    item = provider.current_uploads()[0]
    assert blocker.args == [item.id]
    assert item.status == UploadStatus.WAITING
    assert item.duplicate_conflict is True
    assert item.conflict_policy is None
    assert uploader.calls == [None]

    provider.resolve_duplicate(item.id, ConflictPolicy.RENAME, False)
    qtbot.waitUntil(
        lambda: provider.current_uploads()[0].status == UploadStatus.COMPLETED
    )
    assert uploader.calls == [None, ConflictPolicy.RENAME]
    provider.shutdown()


def test_tc25_skip_does_not_start_a_second_transfer(qtbot, tmp_path: Path) -> None:
    source = tmp_path / "đã tồn tại.txt"
    source.write_bytes(b"x" * 100)
    uploader = ConflictOnceUploader()
    provider = TcpUploadProvider(max_concurrent=1, uploader=uploader)
    with qtbot.waitSignal(provider.duplicate_detected):
        provider.add_files([source])
    item = provider.current_uploads()[0]

    provider.resolve_duplicate(item.id, ConflictPolicy.SKIP, False)

    assert provider.current_uploads()[0].status == UploadStatus.SKIPPED
    assert uploader.calls == [None]
    assert provider.current_history()[0].result == HistoryResult.SKIPPED
    provider.shutdown()


class RetryOnceUploader:
    def __init__(self) -> None:
        self.attempts = 0

    def upload(self, source, *, request_id, batch_id=None, batch_total=1, conflict, on_progress):
        self.attempts += 1
        if self.attempts == 1:
            raise TcpUploadError(
                "connection_error",
                "Không thể kết nối tới máy chủ. Kiểm tra mạng rồi thử lại.",
            )
        on_progress(TransferProgress(100, 100, 100, 500.0))
        return UploadOutcome(UploadStatus.COMPLETED, source.name, 100)

    def health_check(self) -> bool:
        return True


def test_tc22_retry_is_manual_and_replaces_attempt_history(qtbot, tmp_path: Path) -> None:
    source = tmp_path / "thử lại.txt"
    source.write_bytes(b"x" * 100)
    uploader = RetryOnceUploader()
    provider = TcpUploadProvider(max_concurrent=1, uploader=uploader)
    provider.add_files([source])
    qtbot.waitUntil(
        lambda: provider.current_uploads()[0].status == UploadStatus.FAILED
    )
    item = provider.current_uploads()[0]

    qtbot.wait(100)
    assert uploader.attempts == 1
    assert len(provider.current_history()) == 1
    assert provider.current_history()[0].result == HistoryResult.FAILED

    provider.retry_upload(item.id)
    qtbot.waitUntil(
        lambda: provider.current_uploads()[0].status == UploadStatus.COMPLETED
    )
    assert uploader.attempts == 2
    assert len(provider.current_history()) == 1
    assert provider.current_history()[0].id == item.id
    assert provider.current_history()[0].result == HistoryResult.SUCCESS
    provider.shutdown()


class BlockingHistoryUploader:
    def __init__(self, *, fail: bool = False) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self.fail = fail

    def upload(self, source, *, request_id, batch_id=None, batch_total=1, conflict, on_progress):
        return UploadOutcome(UploadStatus.COMPLETED, source.name, source.stat().st_size)

    def health_check(self) -> bool:
        return True

    def load_history(self):
        self.started.set()
        if not self.release.wait(3):
            raise RuntimeError("Test history worker không được giải phóng.")
        if self.fail:
            raise TcpUploadError("history_error", "Không thể tải lịch sử từ máy chủ.")
        return (
            HistoryEntry(
                "history-30",
                "báo cáo persisted.pdf",
                datetime(2026, 8, 24, 9, 0, tzinfo=UTC),
                2048,
                HistoryResult.SUCCESS,
            ),
        )


def test_tc30_history_loads_off_the_ui_thread_and_reports_backend_errors(qtbot) -> None:
    uploader = BlockingHistoryUploader()
    provider = TcpUploadProvider(max_concurrent=1, uploader=uploader)
    loading: list[bool] = []
    provider.history_loading_changed.connect(loading.append)

    provider.refresh_history()
    assert uploader.started.wait(1)
    event_loop_ticked: list[bool] = []
    QTimer.singleShot(0, lambda: event_loop_ticked.append(True))
    qtbot.waitUntil(lambda: bool(event_loop_ticked))
    assert provider.current_history() == ()

    uploader.release.set()
    qtbot.waitUntil(lambda: len(provider.current_history()) == 1)
    assert provider.current_history()[0].name == "báo cáo persisted.pdf"
    assert loading == [True, False]
    provider.shutdown()

    failing = BlockingHistoryUploader(fail=True)
    failed_provider = TcpUploadProvider(max_concurrent=1, uploader=failing)
    errors: list[str] = []
    failed_provider.history_error.connect(errors.append)
    failed_provider.refresh_history()
    assert failing.started.wait(1)
    failing.release.set()
    qtbot.waitUntil(lambda: bool(errors))
    assert errors == ["Không thể tải lịch sử từ máy chủ."]
    failed_provider.shutdown()
