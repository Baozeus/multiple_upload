from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication


CODE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_ROOT / "ui-handoff" / "client"))

from multiple_upload_client.config import ClientConfig
from multiple_upload_client.models import UploadStatus
from multiple_upload_client.tcp_transport import TcpHealthResult, TcpUploadResult
from multiple_upload_client.uploader import UploadCoordinator


def make_config() -> ClientConfig:
    return ClientConfig(
        transport="tcp",
        tcp_host="127.0.0.1",
        tcp_port=9000,
        base_url="",
        upload_endpoint="/api/uploads",
        allow_mock_fallback=False,
        max_concurrent=3,
        max_upload_size=512_000,
        conflict_policy="ask",
    )


class CoordinatorConnectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def _wait_for(self, predicate, timeout: float = 2.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.app.processEvents()
            if predicate():
                return
            time.sleep(0.01)
        self.fail("Qt signal không hoàn tất đúng thời hạn.")

    def test_invalid_endpoint_is_rejected_before_worker_starts(self) -> None:
        coordinator = UploadCoordinator(make_config())
        with self.assertRaisesRegex(ValueError, "không được để trống"):
            coordinator.update_tcp_endpoint("", 9000)
        with self.assertRaisesRegex(ValueError, "1–65535"):
            coordinator.update_tcp_endpoint("127.0.0.1", 70000)

    def test_repeated_click_does_not_start_a_second_probe(self) -> None:
        release = threading.Event()

        def delayed_probe(_adapter):
            release.wait(1)
            return TcpHealthResult(True, 0, 3)

        coordinator = UploadCoordinator(make_config())
        states: list[dict[str, object]] = []
        coordinator.connection_state_changed.connect(states.append)
        with patch(
            "multiple_upload_client.uploader.TcpUploadAdapter.check_server",
            autospec=True,
            side_effect=delayed_probe,
        ) as probe:
            self.assertTrue(coordinator.check_connection())
            self.assertFalse(coordinator.check_connection())
            self.assertEqual(probe.call_count, 1)
            release.set()
            self._wait_for(lambda: states and states[-1].get("state") == "ready")
        self.assertEqual(probe.call_count, 1)

    def test_endpoint_change_discards_stale_probe_result(self) -> None:
        release = threading.Event()

        def delayed_probe(_adapter):
            release.wait(1)
            return TcpHealthResult(True, 0, 3)

        coordinator = UploadCoordinator(make_config())
        states: list[dict[str, object]] = []
        coordinator.connection_state_changed.connect(states.append)
        with patch(
            "multiple_upload_client.uploader.TcpUploadAdapter.check_server",
            autospec=True,
            side_effect=delayed_probe,
        ):
            self.assertTrue(coordinator.check_connection())
            coordinator.update_tcp_endpoint("localhost", 9100)
            release.set()
            self._wait_for(
                lambda: states
                and states[-1].get("busy") is False
                and states[-1].get("state") == "untested"
            )
        self.assertEqual(states[-1]["host"], "localhost")
        self.assertNotIn("ready", [state.get("state") for state in states[-1:]])

    def test_skip_keeps_visible_terminal_item_and_history_signal(self) -> None:
        coordinator = UploadCoordinator(make_config())
        terminal: list[tuple[object, str]] = []
        coordinator.item_terminal.connect(lambda item, status: terminal.append((item, status)))
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "duplicate.txt"
            source.write_text("content", encoding="utf-8")
            item = coordinator.queue.add_paths([source])[0]
            item.conflict_pending = True
            coordinator.resolve_conflict(item.id, "skip")
            self.assertIs(coordinator.get_item(item.id), item)
        self.assertIs(item.status, UploadStatus.SKIPPED)
        self.assertEqual(item.progress, 0)
        self.assertEqual(terminal[0][1], "Bỏ qua")

    def test_three_workers_run_while_the_fourth_waits_without_blocking_ui(self) -> None:
        release = threading.Event()

        def blocked_upload(
            _adapter,
            path,
            conflict="ask",
            on_progress=None,
            on_waiting_for_ack=None,
        ):
            if on_progress is not None:
                on_progress(25, 1024.0)
            release.wait(1)
            if on_progress is not None:
                on_progress(100, 2048.0)
            if on_waiting_for_ack is not None:
                on_waiting_for_ack()
            return TcpUploadResult("SUCCESS", Path(path).name, Path(path).stat().st_size)

        coordinator = UploadCoordinator(make_config())
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for index in range(4):
                path = Path(directory) / f"worker-{index}.txt"
                path.write_text(str(index), encoding="utf-8")
                paths.append(str(path))
            with patch(
                "multiple_upload_client.uploader.TcpUploadAdapter.upload",
                autospec=True,
                side_effect=blocked_upload,
            ):
                started = time.monotonic()
                coordinator.add_files(paths)
                self.assertLess(time.monotonic() - started, 0.2)
                statuses = [item.status for item in coordinator.queue.items.values()]
                self.assertEqual(statuses.count(UploadStatus.UPLOADING), 3)
                self.assertEqual(statuses.count(UploadStatus.WAITING), 1)
                release.set()
                self._wait_for(
                    lambda: all(
                        item.status is UploadStatus.COMPLETED
                        for item in coordinator.queue.items.values()
                    )
                )

    def test_payload_sent_stays_uploading_until_server_ack(self) -> None:
        release_ack = threading.Event()
        waiting_callback_ran = threading.Event()

        def delayed_ack_upload(
            _adapter,
            path,
            conflict="ask",
            on_progress=None,
            on_waiting_for_ack=None,
        ):
            if on_progress is not None:
                on_progress(100, 4096.0)
            if on_waiting_for_ack is not None:
                on_waiting_for_ack()
            waiting_callback_ran.set()
            release_ack.wait(1)
            return TcpUploadResult("SUCCESS", Path(path).name, Path(path).stat().st_size)

        coordinator = UploadCoordinator(make_config())
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "waiting-ack.txt"
            source.write_bytes(b"payload")
            with patch(
                "multiple_upload_client.uploader.TcpUploadAdapter.upload",
                autospec=True,
                side_effect=delayed_ack_upload,
            ):
                coordinator.add_files([str(source)])
                self._wait_for(waiting_callback_ran.is_set)
                item = next(iter(coordinator.queue.items.values()))
                self._wait_for(lambda: item.detail == "Đang chờ Server xác nhận")
                self.assertIs(item.status, UploadStatus.UPLOADING)
                self.assertEqual(item.progress, 99)
                self.assertEqual(item.speed, "—")
                release_ack.set()
                self._wait_for(lambda: item.status is UploadStatus.COMPLETED)

    def test_eight_file_batch_reports_exact_six_accepted_two_rejected_message(self) -> None:
        coordinator = UploadCoordinator(make_config())
        notifications: list[str] = []
        rejected_batches: list[list[tuple[Path, str]]] = []
        coordinator.notification.connect(notifications.append)
        coordinator.rejected_files.connect(rejected_batches.append)

        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for index in range(8):
                path = Path(directory) / f"selected-{index}.txt"
                path.write_text(str(index), encoding="utf-8")
                paths.append(path)
            coordinator.add_files([str(path) for path in paths])

            self.assertIn(
                "Mỗi lần chỉ nhận tối đa 6 file. Đã nhận 6 file; "
                "2 file còn lại chưa được thêm.",
                notifications,
            )
            self.assertEqual(
                [item.path for item in coordinator.queue.items.values()],
                paths[:6],
            )
            self.assertEqual(
                [path for path, _reason in rejected_batches[-1]],
                paths[6:],
            )


if __name__ == "__main__":
    unittest.main()
