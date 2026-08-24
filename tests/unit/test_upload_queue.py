from __future__ import annotations

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from udm10.client.models.upload import ConflictPolicy, UploadItem, UploadStatus
from udm10.client.queue.upload_queue import InvalidStateTransition, UploadQueue


def _items(count: int) -> list[UploadItem]:
    return [
        UploadItem(
            id=f"file-{index}",
            name=f"file-{index}.bin",
            size_bytes=100,
            status=UploadStatus.WAITING,
            source_path=Path(f"file-{index}.bin"),
        )
        for index in range(count)
    ]


def test_n_plus_one_keeps_only_n_uploading_in_fifo_order() -> None:
    queue = UploadQueue(max_concurrent=3)
    queue.enqueue(_items(4))

    claimed = queue.claim_ready()
    snapshot = queue.snapshot()

    assert [item.id for item in claimed] == ["file-0", "file-1", "file-2"]
    assert [item.status for item in snapshot] == [
        UploadStatus.UPLOADING,
        UploadStatus.UPLOADING,
        UploadStatus.UPLOADING,
        UploadStatus.WAITING,
    ]
    assert snapshot[-1].queue_position == 1


def test_tc18_n_plus_five_preserves_fifo_for_every_waiting_file() -> None:
    queue = UploadQueue(max_concurrent=3)
    queue.enqueue(_items(8))

    started = [item.id for item in queue.claim_ready()]
    while any(item.status == UploadStatus.WAITING for item in queue.snapshot()):
        active = next(
            item for item in queue.snapshot() if item.status == UploadStatus.UPLOADING
        )
        queue.finish(active.id, UploadStatus.COMPLETED)
        started.extend(item.id for item in queue.claim_ready())

    assert started == [f"file-{index}" for index in range(8)]
    assert sum(
        item.status == UploadStatus.UPLOADING for item in queue.snapshot()
    ) <= 3


def test_tc19_failed_slot_starts_next_waiting_file() -> None:
    queue = UploadQueue(max_concurrent=2)
    queue.enqueue(_items(4))
    assert [item.id for item in queue.claim_ready()] == ["file-0", "file-1"]

    queue.finish("file-0", UploadStatus.FAILED, error_message="Lỗi cô lập")

    assert [item.id for item in queue.claim_ready()] == ["file-2"]
    assert queue.snapshot()[1].status == UploadStatus.UPLOADING


def test_terminal_result_releases_slot_for_next_fifo_item() -> None:
    queue = UploadQueue(max_concurrent=2)
    queue.enqueue(_items(7))
    assert [item.id for item in queue.claim_ready()] == ["file-0", "file-1"]

    queue.finish("file-0", UploadStatus.COMPLETED)
    next_items = queue.claim_ready()

    assert [item.id for item in next_items] == ["file-2"]
    assert queue.snapshot()[0].status == UploadStatus.COMPLETED
    assert queue.snapshot()[0].progress == 100


def test_progress_and_speed_are_independent_per_upload() -> None:
    queue = UploadQueue(max_concurrent=2)
    queue.enqueue(_items(2))
    queue.claim_ready()

    queue.record_progress("file-0", bytes_sent=25, speed_bytes_per_second=120.0)
    queue.record_progress("file-1", bytes_sent=70, speed_bytes_per_second=980.0)
    first, second = queue.snapshot()

    assert (first.progress, first.speed_bytes_per_second) == (25, 120.0)
    assert (second.progress, second.speed_bytes_per_second) == (70, 980.0)


def test_only_declared_state_transitions_are_allowed() -> None:
    queue = UploadQueue(max_concurrent=1)
    queue.enqueue(_items(2))
    queue.claim_ready()
    queue.finish("file-0", UploadStatus.FAILED, error_message="network")
    queue.retry("file-0")
    queue.skip("file-1")

    first, second = queue.snapshot()
    assert first.status == UploadStatus.WAITING
    assert first.progress == 0
    assert second.status == UploadStatus.SKIPPED
    with pytest.raises(InvalidStateTransition):
        queue.finish("file-0", UploadStatus.COMPLETED)


def test_progress_updates_are_thread_safe() -> None:
    queue = UploadQueue(max_concurrent=6)
    queue.enqueue(_items(6))
    queue.claim_ready()

    def update(item_id: str, speed: float) -> None:
        for sent in range(1, 101):
            queue.record_progress(
                item_id,
                bytes_sent=sent,
                speed_bytes_per_second=speed,
            )

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [
            executor.submit(update, f"file-{index}", float(100 + index))
            for index in range(6)
        ]
        for future in futures:
            future.result()

    assert [item.progress for item in queue.snapshot()] == [100] * 6
    assert [item.speed_bytes_per_second for item in queue.snapshot()] == [
        100.0,
        101.0,
        102.0,
        103.0,
        104.0,
        105.0,
    ]


def test_unresolved_head_conflict_cannot_be_bypassed_in_fifo() -> None:
    queue = UploadQueue(max_concurrent=1)
    conflict, following = _items(2)
    queue.enqueue([conflict.updated(duplicate_conflict=True), following])

    assert queue.claim_ready() == ()
    queue.resolve_conflict("file-0", ConflictPolicy.RENAME)

    assert [item.id for item in queue.claim_ready()] == ["file-0"]


def test_tc21_server_conflict_returns_upload_to_waiting_without_a_default_policy() -> None:
    queue = UploadQueue(max_concurrent=1)
    queue.enqueue(_items(2))
    assert [item.id for item in queue.claim_ready()] == ["file-0"]

    conflicted = queue.defer_conflict("file-0")

    assert conflicted.status == UploadStatus.WAITING
    assert conflicted.duplicate_conflict is True
    assert conflicted.conflict_policy is None
    assert queue.claim_ready() == ()
