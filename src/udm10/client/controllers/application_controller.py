"""Signal coordinator between the UI and a replaceable data provider."""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QDialog

from udm10.client.models.provider import UiDataProvider
from udm10.client.ui.main_window import MainWindow
from udm10.client.widgets.duplicate_dialog import DuplicateDialog


class ApplicationController(QObject):
    def __init__(self, window: MainWindow, provider: UiDataProvider, parent=None) -> None:
        super().__init__(parent)
        self.window = window
        self.provider = provider
        self._active_duplicate_id: str | None = None
        self._pending_duplicate_ids: list[str] = []
        window.upload_view.files_selected.connect(provider.add_files)
        window.upload_view.retry_requested.connect(provider.retry_upload)
        window.upload_view.remove_requested.connect(provider.remove_upload)
        window.upload_view.resolve_requested.connect(self._enqueue_duplicate)
        window.history_view.refresh_requested.connect(provider.refresh_history)
        window.retry_connection_requested.connect(self._retry_connection)
        window.navigation_changed.connect(self._on_navigation_changed)
        provider.uploads_changed.connect(window.set_uploads)
        provider.history_changed.connect(window.set_history)
        provider.history_loading_changed.connect(window.set_history_loading)
        provider.history_error.connect(lambda _message: window.history_view.show_error())
        provider.connection_changed.connect(window.set_online)
        provider.duplicate_detected.connect(self._enqueue_duplicate)
        window.set_uploads(provider.current_uploads())
        window.set_history(provider.current_history())
        window.set_online(True)

    def _on_navigation_changed(self, page: str) -> None:
        if page == "history":
            self.provider.refresh_history()

    def _retry_connection(self) -> None:
        self.window.set_reconnecting(True)
        self.provider.retry_connection()

    def _enqueue_duplicate(self, upload_id: str) -> None:
        if (
            upload_id == self._active_duplicate_id
            or upload_id in self._pending_duplicate_ids
        ):
            return
        self._pending_duplicate_ids.append(upload_id)
        if self._active_duplicate_id is None:
            self._show_next_duplicate()

    def _show_next_duplicate(self) -> None:
        if self._active_duplicate_id is not None or not self._pending_duplicate_ids:
            return
        upload_id = self._pending_duplicate_ids.pop(0)
        item = next(
            (
                entry
                for entry in self.provider.current_uploads()
                if entry.id == upload_id
            ),
            None,
        )
        if item is None or not item.duplicate_conflict:
            QTimer.singleShot(0, self._show_next_duplicate)
            return
        self._active_duplicate_id = upload_id
        dialog = DuplicateDialog(item, self.window)
        try:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                policy = dialog.selected_policy()
                if policy is not None:
                    self.provider.resolve_duplicate(
                        upload_id, policy, dialog.apply_to_remaining()
                    )
        finally:
            self._active_duplicate_id = None
            QTimer.singleShot(0, self._show_next_duplicate)
