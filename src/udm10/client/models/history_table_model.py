"""Qt table and filter models for persistent upload history."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt

from udm10.client.models.history import HistoryEntry, HistoryResult
from udm10.client.models.formatters import format_bytes, format_datetime


class HistoryTableModel(QAbstractTableModel):
    NAME_COLUMN = 0
    TIME_COLUMN = 1
    SIZE_COLUMN = 2
    RESULT_COLUMN = 3
    HEADERS = ("Tên tệp", "Thời gian", "Dung lượng", "Kết quả")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._entries: tuple[HistoryEntry, ...] = ()

    def set_entries(self, entries: Sequence[HistoryEntry]) -> None:
        self.beginResetModel()
        self._entries = tuple(entries)
        self.endResetModel()

    def entry_at(self, row: int) -> HistoryEntry:
        return self._entries[row]

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._entries)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # noqa: N802
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        entry = self._entries[index.row()]
        if role == Qt.ItemDataRole.UserRole:
            return entry.result.value
        if role == Qt.ItemDataRole.ToolTipRole and index.column() == self.NAME_COLUMN:
            return entry.name
        if role == Qt.ItemDataRole.AccessibleTextRole:
            return self._accessible_text(entry)
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if index.column() == self.NAME_COLUMN:
            return entry.name
        if index.column() == self.TIME_COLUMN:
            return format_datetime(entry.completed_at)
        if index.column() == self.SIZE_COLUMN:
            return format_bytes(entry.size_bytes)
        if index.column() == self.RESULT_COLUMN:
            return _result_label(entry.result)
        return None

    @staticmethod
    def _accessible_text(entry: HistoryEntry) -> str:
        return (
            f"{entry.name}, {format_datetime(entry.completed_at)}, "
            f"{format_bytes(entry.size_bytes)}, {_result_label(entry.result)}"
        )


class HistoryFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._query = ""
        self._result: str | None = None
        self.setDynamicSortFilter(True)

    def set_query(self, query: str) -> None:
        self._query = query.casefold().strip()
        self.beginFilterChange()
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def set_result_filter(self, result: str | None) -> None:
        self._result = result or None
        self.beginFilterChange()
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:  # noqa: N802
        model = self.sourceModel()
        if not isinstance(model, HistoryTableModel):
            return True
        entry = model.entry_at(source_row)
        query_matches = not self._query or self._query in entry.name.casefold()
        result_matches = self._result is None or entry.result.value == self._result
        return query_matches and result_matches


def _result_label(result: HistoryResult) -> str:
    return {
        HistoryResult.SUCCESS: "Thành công",
        HistoryResult.FAILED: "Lỗi",
        HistoryResult.RENAMED: "Đã đổi tên",
        HistoryResult.SKIPPED: "Đã bỏ qua",
    }[result]
