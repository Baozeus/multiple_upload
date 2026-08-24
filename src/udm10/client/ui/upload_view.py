"""Primary upload workspace for the Transfer Desk direction."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from udm10.client.models.upload import UploadItem
from udm10.client.ui.icons import line_icon
from udm10.client.ui.theme import COLORS
from udm10.client.widgets.drop_zone import DropZone
from udm10.client.widgets.summary_stats import SummaryStats
from udm10.client.widgets.upload_list import UploadList


class UploadView(QWidget):
    files_selected = Signal(object)
    retry_requested = Signal(str)
    remove_requested = Signal(str)
    resolve_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._header_compact = False
        self._product_header = _ProductHeader()
        self.drop_zone = DropZone()
        self.summary = SummaryStats()
        self.upload_list = UploadList()
        self.upload_list.setMinimumHeight(260)

        self.drop_zone.files_selected.connect(self.files_selected)
        self.upload_list.choose_files_requested.connect(self.drop_zone.choose_files)
        self.upload_list.retry_requested.connect(self.retry_requested)
        self.upload_list.remove_requested.connect(self.remove_requested)
        self.upload_list.resolve_requested.connect(self.resolve_requested)

        self._header_grid = QGridLayout()
        self._header_grid.setContentsMargins(0, 0, 0, 0)
        self._header_grid.setHorizontalSpacing(24)
        self._header_grid.setVerticalSpacing(16)

        queue_title = QLabel("Hàng đợi tải lên")
        queue_title.setObjectName("SectionTitle")

        self._content = QWidget()
        self._content.setMaximumWidth(1440)
        self._content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(24, 22, 24, 24)
        content_layout.setSpacing(14)
        content_layout.addLayout(self._header_grid)
        content_layout.addWidget(self.summary)
        content_layout.addSpacing(2)
        content_layout.addWidget(queue_title)
        content_layout.addWidget(self.upload_list, 1)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch()
        outer.addWidget(self._content, 1)
        outer.addStretch()
        self._apply_header_layout(False)

    def set_items(self, items: Sequence[UploadItem]) -> None:
        self.summary.set_items(items)
        self.upload_list.set_items(items)
        self.drop_zone.setMinimumHeight(106 if items else 132)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        compact = self.width() < 1120
        if compact != self._header_compact:
            self._apply_header_layout(compact)
        margin = 40 if self.width() >= 1700 else 24
        self._content.layout().setContentsMargins(margin, 22, margin, 24)

    def _apply_header_layout(self, compact: bool) -> None:
        self._header_compact = compact
        self._header_grid.removeWidget(self._product_header)
        self._header_grid.removeWidget(self.drop_zone)
        # QGridLayout retains column metadata after widgets move. Reset both
        # columns so the compact drop target occupies the complete work area.
        for column in (0, 1):
            self._header_grid.setColumnMinimumWidth(column, 0)
            self._header_grid.setColumnStretch(column, 0)
        if compact:
            self._header_grid.addWidget(self._product_header, 0, 0)
            self._header_grid.addWidget(self.drop_zone, 1, 0)
            self._header_grid.setColumnStretch(0, 1)
        else:
            self._header_grid.addWidget(self._product_header, 0, 0)
            self._header_grid.addWidget(self.drop_zone, 0, 1)
            self._header_grid.setColumnMinimumWidth(0, 300)
            self._header_grid.setColumnStretch(0, 0)
            self._header_grid.setColumnStretch(1, 1)


class _ProductHeader(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        icon = QLabel()
        icon.setPixmap(line_icon("upload", COLORS["accent"], 30).pixmap(30, 30))
        icon.setFixedSize(34, 34)
        title = QLabel("Multiple Upload")
        title.setObjectName("DisplayTitle")
        subtitle = QLabel("Tải nhiều tệp lên máy chủ nhanh chóng và an toàn")
        subtitle.setObjectName("MutedText")
        subtitle.setWordWrap(True)
        subtitle.setMaximumWidth(320)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(10)
        title_row.addWidget(icon, 0)
        title_row.addWidget(title)
        title_row.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(8)
        layout.addLayout(title_row)
        layout.addWidget(subtitle)
        layout.addStretch()
