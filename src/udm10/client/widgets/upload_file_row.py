"""Responsive upload row with state-specific actions and feedback."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from udm10.client.models.formatters import format_bytes, format_speed
from udm10.client.models.upload import UploadItem, UploadStatus
from udm10.client.ui.icons import line_icon
from udm10.client.ui.theme import COLORS
from udm10.client.widgets.elided_label import ElidedLabel
from udm10.client.widgets.error_message import ErrorMessage
from udm10.client.widgets.file_type_icon import FileTypeIcon
from udm10.client.widgets.progress_bar import UploadProgressBar
from udm10.client.widgets.status_badge import StatusBadge


class UploadFileRow(QFrame):
    retry_requested = Signal(str)
    remove_requested = Signal(str)
    resolve_requested = Signal(str)

    def __init__(self, item: UploadItem, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("UploadRow")
        self._item = item
        self._compact = False

        self._file_icon = FileTypeIcon(item.name)
        self._name = ElidedLabel(item.name)
        self._name.setStyleSheet("font-weight: 600;")
        self._name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._size = QLabel()
        self._size.setObjectName("MutedText")
        self._status = StatusBadge()
        self._progress = UploadProgressBar()
        self._speed = QLabel()
        self._speed.setObjectName("MutedText")
        self._speed.setMinimumWidth(78)
        self._compact_meta = QLabel()
        self._compact_meta.setObjectName("MutedText")

        self._retry = QPushButton("Thử lại")
        self._retry.setIcon(line_icon("retry", COLORS["accent"], 17))
        self._retry.clicked.connect(lambda: self.retry_requested.emit(self._item.id))
        self._resolve = QPushButton("Xử lý")
        self._resolve.clicked.connect(lambda: self.resolve_requested.emit(self._item.id))
        self._remove = QToolButton()
        self._remove.setObjectName("IconButton")
        self._remove.setIcon(line_icon("trash", COLORS["muted"], 18))
        self._remove.setToolTip("Xóa khỏi danh sách")
        self._remove.setAccessibleName("Xóa tệp khỏi danh sách")
        self._remove.clicked.connect(lambda: self.remove_requested.emit(self._item.id))

        self._actions = QWidget()
        action_layout = QHBoxLayout(self._actions)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(6)
        action_layout.addStretch()
        action_layout.addWidget(self._resolve)
        action_layout.addWidget(self._retry)
        action_layout.addWidget(self._remove)

        self._error = ErrorMessage()
        self._error.setVisible(False)

        self._file_cell = QWidget()
        file_layout = QHBoxLayout(self._file_cell)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(12)
        file_layout.addWidget(self._file_icon)
        file_layout.addWidget(self._name, 1)

        self._layout = QGridLayout(self)
        # The extra right inset keeps the 38px action target clear of an
        # overlaid vertical scrollbar on Windows at 1366px-wide layouts.
        self._layout.setContentsMargins(16, 11, 22, 11)
        self._layout.setHorizontalSpacing(16)
        self._layout.setVerticalSpacing(8)
        self.set_item(item)
        self._apply_layout(False)

    @property
    def upload_id(self) -> str:
        return self._item.id

    def set_item(self, item: UploadItem) -> None:
        self._item = item
        self._file_icon.set_filename(item.name)
        self._name.setText(item.name)
        size_text = format_bytes(item.size_bytes)
        speed_text = format_speed(item.speed_bytes_per_second)
        self._size.setText(size_text)
        self._speed.setText(speed_text)
        self._compact_meta.setText(f"{size_text}  •  {speed_text}")

        if item.duplicate_conflict:
            self._status.set_status(
                text="Cần xử lý", icon_name="warning", color=COLORS["warning"]
            )
            row_state = "conflict"
        else:
            status_map = {
                UploadStatus.WAITING: ("Đang chờ", "clock", COLORS["muted"]),
                UploadStatus.UPLOADING: ("Đang tải", "upload", COLORS["accent"]),
                UploadStatus.COMPLETED: ("Hoàn tất", "check", COLORS["success"]),
                UploadStatus.FAILED: ("Lỗi", "error", COLORS["error"]),
                UploadStatus.SKIPPED: ("Đã bỏ qua", "close", COLORS["muted"]),
            }
            text, icon_name, color = status_map[item.status]
            self._status.set_status(text=text, icon_name=icon_name, color=color)
            row_state = "failed" if item.status == UploadStatus.FAILED else item.status.value

        active_progress = item.status in {UploadStatus.UPLOADING, UploadStatus.COMPLETED}
        self._progress.set_progress(item.progress, active=active_progress)
        self._resolve.setVisible(item.duplicate_conflict)
        self._retry.setVisible(item.status == UploadStatus.FAILED)
        self._remove.setVisible(item.status != UploadStatus.UPLOADING)

        if item.status == UploadStatus.WAITING and not item.duplicate_conflict:
            waiting_text = (
                f"Thứ {item.queue_position} trong hàng đợi"
                if item.queue_position
                else "Đang chờ lượt"
            )
            self._speed.setText(waiting_text)
            self._compact_meta.setText(f"{size_text}  •  {waiting_text}")
        elif item.status == UploadStatus.COMPLETED:
            self._speed.setText("Đã tải lên")
            self._compact_meta.setText(f"{size_text}  •  Đã tải lên")
        elif item.status == UploadStatus.SKIPPED:
            self._speed.setText("Không tải lên")
            self._compact_meta.setText(f"{size_text}  •  Không tải lên")

        self._error.setVisible(bool(item.error_message))
        if item.error_message:
            self._error.set_message(item.error_message)
        self._update_minimum_height()

        self.setProperty("rowState", row_state)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setAccessibleName(
            f"{item.name}, {self._status.accessibleName()}, {size_text}"
        )

    def set_compact(self, compact: bool) -> None:
        if compact == self._compact:
            return
        self._apply_layout(compact)

    def _apply_layout(self, compact: bool) -> None:
        self._compact = compact
        widgets = (
            self._file_cell,
            self._size,
            self._status,
            self._progress,
            self._speed,
            self._compact_meta,
            self._actions,
            self._error,
        )
        for widget in widgets:
            self._layout.removeWidget(widget)

        if compact:
            self._layout.addWidget(self._file_cell, 0, 0, 1, 2)
            self._layout.addWidget(self._status, 0, 2)
            self._layout.addWidget(self._actions, 0, 3)
            self._layout.addWidget(self._progress, 1, 0, 1, 2)
            self._layout.addWidget(self._compact_meta, 1, 2, 1, 2)
            self._layout.addWidget(self._error, 2, 0, 1, 4)
            self._size.hide()
            self._speed.hide()
            self._compact_meta.show()
            self._layout.setColumnStretch(0, 4)
            self._layout.setColumnStretch(1, 2)
        else:
            self._layout.addWidget(self._file_cell, 0, 0)
            self._layout.addWidget(self._size, 0, 1)
            self._layout.addWidget(self._status, 0, 2)
            self._layout.addWidget(self._progress, 0, 3)
            self._layout.addWidget(self._speed, 0, 4)
            self._layout.addWidget(self._actions, 0, 5)
            self._layout.addWidget(self._error, 1, 0, 1, 6)
            self._size.show()
            self._speed.show()
            self._compact_meta.hide()
            self._layout.setColumnStretch(0, 5)
            self._layout.setColumnStretch(3, 3)
        self._update_minimum_height()

    def _update_minimum_height(self) -> None:
        base = 88 if self._compact else 66
        self.setMinimumHeight(base + (46 if self._error.isVisible() else 0))
