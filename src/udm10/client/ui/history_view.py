"""Searchable history workspace with explicit loading/empty/error states."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QModelIndex, QRect, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QApplication, QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel, QStackedWidget, QStyle, QStyledItemDelegate, QStyleOptionViewItem, QTableView, QVBoxLayout, QWidget

from udm10.client.models.history import HistoryEntry, HistoryResult
from udm10.client.models.history_table_model import HistoryFilterProxyModel, HistoryTableModel
from udm10.client.ui.icons import line_icon
from udm10.client.ui.theme import COLORS
from udm10.client.widgets.empty_state import EmptyState
from udm10.client.widgets.search_filter_bar import SearchAndFilterBar


class HistoryView(QWidget):
    upload_navigation_requested = Signal()
    refresh_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._loading = False
        self._source = HistoryTableModel(self)
        self._proxy = HistoryFilterProxyModel(self)
        self._proxy.setSourceModel(self._source)
        self._proxy.modelReset.connect(self._update_result_state)
        self._proxy.rowsInserted.connect(self._update_result_state)
        self._proxy.rowsRemoved.connect(self._update_result_state)

        title = QLabel("Lịch sử upload")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Xem lại thời gian, dung lượng và kết quả của các tệp đã xử lý.")
        subtitle.setObjectName("MutedText")

        self.toolbar = SearchAndFilterBar()
        self.toolbar.search_changed.connect(self._on_search)
        self.toolbar.filter_changed.connect(self._on_filter)

        self.table = QTableView()
        self.table.setModel(self._proxy)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.horizontalHeader().setMinimumHeight(42)
        self.table.horizontalHeader().setSectionResizeMode(HistoryTableModel.NAME_COLUMN, QHeaderView.ResizeMode.Stretch)
        for column in (HistoryTableModel.TIME_COLUMN, HistoryTableModel.SIZE_COLUMN):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(
            HistoryTableModel.RESULT_COLUMN, QHeaderView.ResizeMode.Fixed
        )
        self.table.setColumnWidth(HistoryTableModel.RESULT_COLUMN, 148)
        self.table.setItemDelegateForColumn(HistoryTableModel.RESULT_COLUMN, _HistoryResultDelegate(self.table))

        self._loading_state = _LoadingHistory()
        self._empty_state = EmptyState(icon_name="history", title="Chưa có lịch sử upload", description="Khi một tệp được xử lý, kết quả sẽ xuất hiện ở đây.", action_text="Tải tệp")
        self._empty_state.action_requested.connect(self.upload_navigation_requested)
        self._no_results = EmptyState(icon_name="search", title="Không tìm thấy tệp phù hợp", description="Thử từ khóa khác hoặc bỏ bộ lọc trạng thái hiện tại.", action_text="Xóa tìm kiếm và bộ lọc")
        self._no_results.action_requested.connect(self.toolbar.clear_filters)
        self._error_state = _HistoryErrorState()
        self._error_state.retry_requested.connect(self.refresh_requested)

        self._stack = QStackedWidget()
        for widget in (self.table, self._loading_state, self._empty_state, self._no_results, self._error_state):
            self._stack.addWidget(widget)

        content = QWidget()
        content.setMaximumWidth(1440)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 26, 24, 24)
        content_layout.setSpacing(14)
        content_layout.addWidget(title)
        content_layout.addWidget(subtitle)
        content_layout.addSpacing(6)
        content_layout.addWidget(self.toolbar)
        content_layout.addWidget(self._stack, 1)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch()
        outer.addWidget(content, 1)
        outer.addStretch()
        self._content = content
        self._update_result_state()

    def set_entries(self, entries: Sequence[HistoryEntry]) -> None:
        self._source.set_entries(entries)
        self._update_result_state()

    def set_loading(self, loading: bool) -> None:
        self._loading = loading
        self.toolbar.setDisabled(loading)
        self._update_result_state()

    def show_error(self) -> None:
        self._loading = False
        self.toolbar.setEnabled(True)
        self._stack.setCurrentWidget(self._error_state)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        margin = 40 if self.width() >= 1700 else 24
        self._content.layout().setContentsMargins(margin, 26, margin, 24)

    def _on_search(self, query: str) -> None:
        self._proxy.set_query(query)
        self._update_result_state()

    def _on_filter(self, result: str | None) -> None:
        self._proxy.set_result_filter(result)
        self._update_result_state()

    def _update_result_state(self, *_args) -> None:
        if self._loading:
            target = self._loading_state
        elif self._source.rowCount() == 0:
            target = self._empty_state
        elif self._proxy.rowCount() == 0:
            target = self._no_results
        else:
            target = self.table
        self._stack.setCurrentWidget(target)


class _HistoryResultDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        result = HistoryResult(index.data(Qt.ItemDataRole.UserRole))
        label, icon_name, color = {
            HistoryResult.SUCCESS: ("Thành công", "check", COLORS["success"]),
            HistoryResult.FAILED: ("Lỗi", "error", COLORS["error"]),
            HistoryResult.RENAMED: ("Đã đổi tên", "retry", COLORS["accent"]),
            HistoryResult.SKIPPED: ("Đã bỏ qua", "clock", COLORS["muted"]),
        }[result]
        styled = QStyleOptionViewItem(option)
        self.initStyleOption(styled, index)
        styled.text = ""
        style = styled.widget.style() if styled.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, styled, painter, styled.widget)
        icon_rect = QRect(option.rect.left() + 12, option.rect.center().y() - 9, 18, 18)
        line_icon(icon_name, color, 18).paint(painter, icon_rect)
        text_rect = option.rect.adjusted(40, 0, -8, 0)
        painter.save()
        painter.setPen(QColor(color))
        font = painter.font()
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, label)
        painter.restore()


class _LoadingHistory(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Surface")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        for index in range(7):
            row = QHBoxLayout()
            row.setSpacing(24)
            for width in (260 + (index % 3) * 54, 150, 90, 120):
                bar = QFrame()
                bar.setFixedSize(width, 14)
                bar.setStyleSheet("background: #E4E9EF; border-radius: 4px;")
                row.addWidget(bar)
            row.addStretch()
            layout.addLayout(row)
        layout.addStretch()
        self.setAccessibleName("Đang tải lịch sử")


class _HistoryErrorState(EmptyState):
    retry_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(icon_name="error", title="Không thể tải lịch sử", description="Kiểm tra kết nối hoặc cấu hình lưu trữ rồi thử lại.", action_text="Thử lại", parent=parent)
        self.action_requested.connect(self.retry_requested)
