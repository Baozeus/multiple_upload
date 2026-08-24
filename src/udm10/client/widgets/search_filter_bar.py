"""History search and status filter with clear semantics."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QWidget

from udm10.client.models.history import HistoryResult
from udm10.client.ui.icons import line_icon
from udm10.client.ui.theme import COLORS


class SearchAndFilterBar(QWidget):
    search_changed = Signal(str)
    filter_changed = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Tìm theo tên tệp…")
        self.search.setClearButtonEnabled(True)
        self.search.addAction(
            line_icon("search", COLORS["muted"], 18),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        self.search.textChanged.connect(self.search_changed)
        self.search.setAccessibleName("Tìm kiếm lịch sử theo tên tệp")

        self.filter = QComboBox()
        self.filter.setMinimumWidth(176)
        self.filter.addItem("Tất cả trạng thái", None)
        self.filter.addItem("Thành công", HistoryResult.SUCCESS.value)
        self.filter.addItem("Lỗi", HistoryResult.FAILED.value)
        self.filter.addItem("Đã đổi tên", HistoryResult.RENAMED.value)
        self.filter.addItem("Đã bỏ qua", HistoryResult.SKIPPED.value)
        self.filter.currentIndexChanged.connect(
            lambda _index: self.filter_changed.emit(self.filter.currentData())
        )
        self.filter.setAccessibleName("Lọc lịch sử theo trạng thái")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self.search, 1)
        layout.addWidget(self.filter)

    def clear_filters(self) -> None:
        self.search.clear()
        self.filter.setCurrentIndex(0)
