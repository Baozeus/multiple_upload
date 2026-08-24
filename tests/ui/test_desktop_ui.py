from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QRadioButton

from udm10.client.controllers import ApplicationController
from udm10.client.models.mock_provider import MockUiDataProvider
from udm10.client.models.upload import ConflictPolicy, UploadItem, UploadStatus
from udm10.client.ui.main_window import MainWindow
from udm10.client.widgets.duplicate_dialog import DuplicateDialog


def _window(qtbot):
    provider = MockUiDataProvider(auto_advance=False)
    window = MainWindow("127.0.0.1", 9000)
    controller = ApplicationController(window, provider, parent=window)
    window.setProperty("testController", controller)
    qtbot.addWidget(window)
    window.show()
    return window, provider


def test_mixed_scenario_renders_ten_keyed_rows(qtbot) -> None:
    window, provider = _window(qtbot)
    qtbot.waitExposed(window)
    assert len(provider.current_uploads()) == 10
    assert len(window.upload_view.upload_list._rows) == 10
    assert window.minimumWidth() == 960
    assert window.minimumHeight() == 640


def test_drop_zone_accepts_real_local_file_urls(qtbot, tmp_path: Path) -> None:
    window, _provider = _window(qtbot)
    file_path = tmp_path / "tệp Unicode.txt"
    file_path.write_text("demo", encoding="utf-8")
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(file_path))])
    drag = QDragEnterEvent(
        QPoint(20, 20),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.upload_view.drop_zone.dragEnterEvent(drag)
    assert drag.isAccepted()
    assert window.upload_view.drop_zone.property("dragActive") is True

    drop = QDropEvent(
        QPointF(20, 20),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    with qtbot.waitSignal(window.upload_view.drop_zone.files_selected) as blocker:
        window.upload_view.drop_zone.dropEvent(drop)
    assert blocker.args[0] == [file_path]


def test_drop_zone_is_keyboard_operable(qtbot) -> None:
    window, _provider = _window(qtbot)
    zone = window.upload_view.drop_zone
    invoked: list[bool] = []
    zone.choose_files = lambda: invoked.append(True)
    zone.setFocus()
    qtbot.keyClick(zone, Qt.Key.Key_Return)
    assert invoked == [True]


def test_tc03_file_picker_emits_every_selected_file(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    window, _provider = _window(qtbot)
    paths = [tmp_path / name for name in ("a.txt", "b.pdf", "ảnh.jpg", "hợp đồng.docx")]
    for path in paths:
        path.write_bytes(b"fixture")
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileNames",
        lambda *_args, **_kwargs: ([str(path) for path in paths], ""),
    )

    with qtbot.waitSignal(window.upload_view.drop_zone.files_selected) as blocker:
        window.upload_view.drop_zone.choose_files()

    assert blocker.args[0] == paths


def test_tc30_history_search_filter_and_no_results_state(qtbot) -> None:
    window, _provider = _window(qtbot)
    window.set_page("history")
    window.set_history_loading(False)
    failed_index = window.history_view.toolbar.filter.findData("failed")
    window.history_view.toolbar.filter.setCurrentIndex(failed_index)
    qtbot.waitUntil(lambda: window.history_view._proxy.rowCount() > 0)
    assert all(
        window.history_view._proxy.index(row, 3).data(Qt.ItemDataRole.UserRole)
        == "failed"
        for row in range(window.history_view._proxy.rowCount())
    )
    window.history_view.toolbar.clear_filters()
    window.history_view.toolbar.search.setText("không-có-tệp-này")
    qtbot.waitUntil(lambda: window.history_view._proxy.rowCount() == 0)
    assert window.history_view._stack.currentWidget() is window.history_view._no_results


def test_duplicate_dialog_requires_an_explicit_choice(qtbot) -> None:
    _window_instance, provider = _window(qtbot)
    item = next(item for item in provider.current_uploads() if item.duplicate_conflict)
    dialog = DuplicateDialog(item)
    qtbot.addWidget(dialog)
    dialog.show()
    radios = dialog.findChildren(QRadioButton)
    assert len(radios) == 3
    assert dialog.selected_policy() is None
    assert dialog._continue.isEnabled() is False
    radios[1].click()
    assert dialog.selected_policy() == ConflictPolicy.RENAME
    assert dialog._continue.isEnabled() is True


def test_overwrite_choice_is_a_clearly_destructive_keyboard_action(qtbot) -> None:
    _window_instance, provider = _window(qtbot)
    item = next(item for item in provider.current_uploads() if item.duplicate_conflict)
    dialog = DuplicateDialog(item)
    qtbot.addWidget(dialog)
    dialog.show()
    overwrite = dialog.findChildren(QRadioButton)[0]
    overwrite.setFocus()

    qtbot.keyClick(overwrite, Qt.Key.Key_Space)

    assert dialog.selected_policy() == ConflictPolicy.OVERWRITE
    assert dialog._continue.objectName() == "DangerButton"
    assert dialog._continue.text() == "Ghi đè tệp"
    assert overwrite.focusPolicy() == Qt.FocusPolicy.StrongFocus


def test_tc21_server_duplicate_signal_opens_dialog_automatically(qtbot) -> None:
    window, provider = _window(qtbot)
    item = next(item for item in provider.current_uploads() if item.duplicate_conflict)
    opened: list[str] = []

    def close_dialog() -> None:
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, DuplicateDialog) and widget.isVisible():
                opened.append(widget.accessibleName())
                widget.reject()

    QTimer.singleShot(0, close_dialog)
    provider.duplicate_detected.emit(item.id)

    assert opened == [f"Xử lý tệp trùng tên {item.name}"]
    assert provider.current_uploads()[5].duplicate_conflict is True


def test_concurrent_conflicts_never_stack_modal_dialogs(qtbot) -> None:
    window, provider = _window(qtbot)
    uploads = list(provider.current_uploads())
    uploads[6] = uploads[6].updated(duplicate_conflict=True)
    provider.set_uploads(uploads)
    conflict_ids = [item.id for item in provider.current_uploads() if item.duplicate_conflict]
    visible_counts: list[int] = []

    def reject_one_visible_dialog() -> None:
        dialogs = [
            widget
            for widget in QApplication.topLevelWidgets()
            if isinstance(widget, DuplicateDialog) and widget.isVisible()
        ]
        visible_counts.append(len(dialogs))
        if dialogs:
            dialogs[-1].reject()

    QTimer.singleShot(0, lambda: provider.duplicate_detected.emit(conflict_ids[1]))
    QTimer.singleShot(20, reject_one_visible_dialog)
    QTimer.singleShot(40, reject_one_visible_dialog)
    provider.duplicate_detected.emit(conflict_ids[0])

    qtbot.waitUntil(lambda: len(visible_counts) == 2)
    assert visible_counts == [1, 1]


def test_long_unicode_name_is_preserved_for_accessibility(qtbot) -> None:
    window, provider = _window(qtbot)
    long_item = max(provider.current_uploads(), key=lambda item: len(item.name))
    row = window.upload_view.upload_list.row_for(long_item.id)
    assert row is not None
    assert row._name.full_text() == long_item.name
    assert row._name.toolTip() == long_item.name


def test_offline_interrupts_active_uploads_without_stopping_waiting_files(qtbot) -> None:
    window, provider = _window(qtbot)
    provider.set_online(False)
    statuses = [item.status for item in provider.current_uploads()]
    assert UploadStatus.UPLOADING not in statuses
    assert UploadStatus.WAITING in statuses
    assert window.offline_banner.isVisible()


def test_history_error_and_reconnecting_states_are_reachable(qtbot) -> None:
    window, provider = _window(qtbot)
    window.set_page("history")
    window.history_view.show_error()
    assert window.history_view._stack.currentWidget() is window.history_view._error_state
    provider.set_online(False)
    window.set_reconnecting(True)
    assert window.offline_banner._button.isEnabled() is False
    assert window.offline_banner._button.text() == "Đang kết nối…"


def test_skipped_upload_remains_visible_with_explicit_status(qtbot) -> None:
    window, provider = _window(qtbot)
    conflict = next(item for item in provider.current_uploads() if item.duplicate_conflict)

    provider.resolve_duplicate(conflict.id, ConflictPolicy.SKIP, False)
    skipped = next(item for item in provider.current_uploads() if item.id == conflict.id)
    row = window.upload_view.upload_list.row_for(conflict.id)

    assert skipped.status == UploadStatus.SKIPPED
    assert row is not None
    assert row._status.accessibleName() == "Đã bỏ qua"


def test_tc32_long_list_scrolls_and_keeps_keyboard_navigation_responsive(qtbot) -> None:
    window, provider = _window(qtbot)
    items = [
        UploadItem(
            id=f"long-list-{index}",
            name=f"Tệp tiếng Việt số {index:03d} — tên dài để kiểm tra cuộn.pdf",
            size_bytes=1024 + index,
            status=UploadStatus.WAITING,
        )
        for index in range(100)
    ]

    provider.set_uploads(items)
    qtbot.waitUntil(lambda: len(window.upload_view.upload_list._rows) == 100)
    scroll = window.upload_view.upload_list._scroll.verticalScrollBar()
    assert scroll.maximum() > 0

    qtbot.keyClick(window._history_nav, Qt.Key.Key_Space)
    assert window._pages.currentWidget() is window.history_view
