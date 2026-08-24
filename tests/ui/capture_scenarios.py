"""Capture deterministic screenshots for bounded visual QA."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

# Offscreen rendering preserves exact requested pixel sizes. PySide 6.11 does
# not expose Windows system fonts through that plugin, so the QA bootstrap adds
# Segoe UI explicitly below without bundling or modifying the OS font file.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from udm10.client.controllers import ApplicationController
from udm10.client.models.mock_provider import MockUiDataProvider
from udm10.client.ui.main_window import MainWindow
from udm10.client.widgets.duplicate_dialog import DuplicateDialog


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication([])
    if os.name == "nt":
        fonts_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        loaded = False
        for font_name in ("segoeui.ttf", "msyh.ttc", "arial.ttf"):
            font_path = fonts_dir / font_name
            if font_path.is_file():
                loaded = QFontDatabase.addApplicationFont(str(font_path)) >= 0 or loaded
        if loaded:
            app.setFont(QFont("Segoe UI", 10))
    provider = MockUiDataProvider(auto_advance=False)
    window = MainWindow("127.0.0.1", 9000)
    controller = ApplicationController(window, provider, parent=window)
    window.setProperty("captureController", controller)

    window.set_page("upload")
    _capture(app, window, (1366, 768), args.output / "upload-mixed-1366x768.png")
    _capture(app, window, (1920, 1080), args.output / "upload-mixed-1920x1080.png")
    _capture(app, window, (960, 640), args.output / "upload-mixed-960x640.png")

    provider.load_empty_scenario()
    _capture(app, window, (1366, 768), args.output / "upload-empty.png")
    window.upload_view.drop_zone.set_drag_active(True)
    _capture(app, window, (1366, 768), args.output / "upload-drag-over.png")
    window.upload_view.drop_zone.set_drag_active(False)

    provider.load_mixed_scenario()
    window.set_uploads(provider.current_uploads())
    provider.set_online(False)
    _capture(app, window, (1366, 768), args.output / "upload-offline.png")
    window.set_reconnecting(True)
    _capture(app, window, (1366, 768), args.output / "upload-reconnecting.png")
    provider.set_online(True)

    duplicate = next(item for item in provider.current_uploads() if item.duplicate_conflict)
    dialog = DuplicateDialog(duplicate, window)
    dialog.show()
    _process(app)
    dialog.grab().save(str(args.output / "duplicate-dialog.png"))
    dialog._radios[0].click()
    _process(app)
    dialog.grab().save(str(args.output / "duplicate-dialog-overwrite.png"))
    dialog.close()

    window.set_page("history")
    window.set_history_loading(False)
    window.set_history(provider.current_history())
    _capture(app, window, (1366, 768), args.output / "history-populated.png")
    window.set_history([])
    _capture(app, window, (1366, 768), args.output / "history-empty.png")
    window.set_history_loading(True)
    _capture(app, window, (1366, 768), args.output / "history-loading.png")
    window.set_history_loading(False)
    window.set_history(provider.current_history())
    window.history_view.toolbar.search.setText("không-có-tệp-này")
    _capture(app, window, (1366, 768), args.output / "history-no-results.png")
    window.history_view.toolbar.clear_filters()
    window.history_view.show_error()
    _capture(app, window, (1366, 768), args.output / "history-error.png")

    window.close()
    QCoreApplication.processEvents()
    return 0


def _capture(app: QApplication, window: MainWindow, size: tuple[int, int], path: Path) -> None:
    window.resize(*size)
    window.show()
    _process(app)
    if not window.grab().save(str(path)):
        raise RuntimeError(f"Không thể lưu screenshot: {path}")


def _process(app: QApplication) -> None:
    for _ in range(4):
        app.processEvents()


if __name__ == "__main__":
    raise SystemExit(main())
