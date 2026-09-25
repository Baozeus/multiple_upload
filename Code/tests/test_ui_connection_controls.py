from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QApplication


CODE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_ROOT / "ui-handoff" / "client"))

from multiple_upload_client.config import ClientConfig
from multiple_upload_client.history import HistoryStore
from multiple_upload_client.main_window import MainWindow
from multiple_upload_client.models import UploadStatus


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


class ConnectionControlsUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        history = HistoryStore(Path(self.temporary_directory.name) / "history.json")
        self.window = MainWindow(make_config(), history)
        self.app.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.temporary_directory.cleanup()

    def test_connection_controls_are_explicit_and_legacy_menu_is_removed(self) -> None:
        self.assertEqual(self.window.host_input.text(), "127.0.0.1")
        self.assertEqual(self.window.port_input.text(), "9000")
        self.assertEqual(self.window.check_connection_button.text(), "Kiểm tra kết nối")
        self.assertEqual(self.window.connection_badge.label.text(), "Chưa kiểm tra")
        self.assertIn("500 KiB", self.window.drop_zone.note.text())
        self.assertFalse(hasattr(self.window, "conflict_select"))

    def test_connection_state_copy_distinguishes_ready_busy_and_protocol_error(self) -> None:
        self.window._set_connection_state({
            "state": "ready",
            "message": "Server UDM sẵn sàng nhận tệp",
            "host": "127.0.0.1",
            "port": 9000,
            "active_uploads": 0,
            "upload_limit": 3,
            "checked_at": "2026-09-24T18:00:00+07:00",
            "busy": False,
        })
        self.assertEqual(
            self.window.connection_badge.label.text(),
            "Server UDM sẵn sàng · 18:00:00",
        )
        self.assertIn("Kiểm tra gần nhất", self.window.connection_badge.toolTip())
        self.window._set_connection_state({
            "state": "busy",
            "message": "Server UDM phản hồi nhưng đã đủ slot upload",
            "host": "127.0.0.1",
            "port": 9000,
            "active_uploads": 3,
            "upload_limit": 3,
            "busy": False,
        })
        self.assertIn("hết slot", self.window.connection_badge.label.text())
        self.window._set_connection_state({
            "state": "protocol_error",
            "message": "Không đúng giao thức",
            "host": "127.0.0.1",
            "port": 9000,
            "busy": False,
        })
        self.assertEqual(
            self.window.connection_badge.label.text(), "Không đúng giao thức UDM"
        )

    def test_drop_zone_emits_all_dropped_local_files(self) -> None:
        captured: list[list[str]] = []
        self.window.drop_zone.files_dropped.connect(captured.append)
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name in ("tài-liệu.txt", "ảnh.jpg"):
                path = Path(directory) / name
                path.write_bytes(b"test")
                paths.append(path)
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(path)) for path in paths])
            event = QDropEvent(
                QPointF(20, 20),
                Qt.DropAction.CopyAction,
                mime,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
            self.window.drop_zone.dropEvent(event)
        self.assertEqual(
            [[Path(value).resolve() for value in group] for group in captured],
            [[path.resolve() for path in paths]],
        )
        self.assertEqual(
            [item.path for item in self.window.coordinator.queue.items.values()],
            [path.resolve() for path in paths],
        )

    def test_endpoint_fields_are_locked_until_waiting_and_uploading_items_finish(self) -> None:
        source = Path(self.temporary_directory.name) / "endpoint-lock.txt"
        source.write_bytes(b"test")
        item = self.window.coordinator.queue.add_paths([source])[0]
        self.window.coordinator.queue.take_next()
        self.window._refresh_summary()
        self.assertFalse(self.window.host_input.isEnabled())
        self.assertFalse(self.window.port_input.isEnabled())

        item.status = UploadStatus.COMPLETED
        self.window._refresh_summary()
        self.assertTrue(self.window.host_input.isEnabled())
        self.assertTrue(self.window.port_input.isEnabled())


if __name__ == "__main__":
    unittest.main()
