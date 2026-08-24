"""Keyed, scrollable upload list that updates rows in place."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from udm10.client.models.upload import UploadItem
from udm10.client.widgets.empty_state import EmptyState
from udm10.client.widgets.upload_file_row import UploadFileRow


class UploadList(QFrame):
    retry_requested = Signal(str)
    remove_requested = Signal(str)
    resolve_requested = Signal(str)
    choose_files_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Surface")
        self._rows: dict[str, UploadFileRow] = {}
        self._compact = False

        self._header = _UploadHeader()
        self._container = QWidget()
        self._rows_layout = QVBoxLayout(self._container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(0)
        self._rows_layout.addStretch()

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(self._container)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._empty = EmptyState(
            icon_name="upload",
            title="Chưa có tệp trong hàng đợi",
            description="Các tệp bạn thêm sẽ xuất hiện ở đây với trạng thái riêng.",
            action_text="Chọn tệp",
        )
        self._empty.action_requested.connect(self.choose_files_requested)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._scroll)
        self._stack.addWidget(self._empty)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._header)
        layout.addWidget(self._stack, 1)
        self.set_items(())

    def set_items(self, items: Sequence[UploadItem]) -> None:
        incoming_ids = {item.id for item in items}
        for upload_id in tuple(self._rows):
            if upload_id not in incoming_ids:
                row = self._rows.pop(upload_id)
                self._rows_layout.removeWidget(row)
                row.deleteLater()

        for item in items:
            row = self._rows.get(item.id)
            if row is None:
                row = UploadFileRow(item)
                row.retry_requested.connect(self.retry_requested)
                row.remove_requested.connect(self.remove_requested)
                row.resolve_requested.connect(self.resolve_requested)
                row.set_compact(self._compact)
                self._rows[item.id] = row
            else:
                row.set_item(item)
            self._rows_layout.removeWidget(row)
            self._rows_layout.insertWidget(self._rows_layout.count() - 1, row)

        has_items = bool(items)
        self._header.setVisible(has_items)
        self._stack.setCurrentWidget(self._scroll if has_items else self._empty)

    def row_for(self, upload_id: str) -> UploadFileRow | None:
        return self._rows.get(upload_id)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        compact = self.width() < 1040
        if compact == self._compact:
            return
        self._compact = compact
        self._header.set_compact(compact)
        for row in self._rows.values():
            row.set_compact(compact)


class _UploadHeader(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: #EEF2F6; border-bottom: 1px solid #D6DEE8;")
        self.setFixedHeight(42)
        self._labels = [
            QLabel("TỆP"),
            QLabel("DUNG LƯỢNG"),
            QLabel("TRẠNG THÁI"),
            QLabel("TIẾN TRÌNH"),
            QLabel("TỐC ĐỘ"),
            QLabel("HÀNH ĐỘNG"),
        ]
        for label in self._labels:
            label.setObjectName("Caption")
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(16, 0, 22, 0)
        self._layout.setHorizontalSpacing(16)
        self.set_compact(False)

    def set_compact(self, compact: bool) -> None:
        for column in range(6):
            self._layout.setColumnStretch(column, 0)
        for label in self._labels:
            self._layout.removeWidget(label)
            label.setVisible(not compact)
        if compact:
            self._labels[0].setText("TỆP VÀ TIẾN TRÌNH")
            self._labels[0].setVisible(True)
            self._labels[0].setParent(self)
            self._layout.addWidget(self._labels[0], 0, 0, 1, 4)
        else:
            self._labels[0].setText("TỆP")
            for column, label in enumerate(self._labels):
                label.setVisible(True)
                self._layout.addWidget(label, 0, column)
            self._layout.setColumnStretch(0, 5)
            self._layout.setColumnStretch(3, 3)
