"""Five metrics on one restrained strip, not five independent cards."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from udm10.client.models.upload import UploadItem, UploadStatus
from udm10.client.ui.icons import line_icon
from udm10.client.ui.theme import COLORS


class SummaryStats(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SummaryStrip")
        self._metrics = {
            "total": _Metric("Tổng số tệp", None, COLORS["text"]),
            "uploading": _Metric("Đang tải", "upload", COLORS["accent"]),
            "waiting": _Metric("Đang chờ", "clock", COLORS["muted"]),
            "completed": _Metric("Thành công", "check", COLORS["success"]),
            "failed": _Metric("Lỗi", "error", COLORS["error"]),
        }
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(0)
        for index, metric in enumerate(self._metrics.values()):
            if index:
                divider = QFrame()
                divider.setObjectName("SummaryDivider")
                divider.setFixedHeight(38)
                layout.addWidget(divider)
            layout.addWidget(metric, 1)

    def set_items(self, items: Sequence[UploadItem]) -> None:
        counts = {
            "total": len(items),
            "uploading": sum(item.status == UploadStatus.UPLOADING for item in items),
            "waiting": sum(item.status == UploadStatus.WAITING for item in items),
            "completed": sum(item.status == UploadStatus.COMPLETED for item in items),
            "failed": sum(item.status == UploadStatus.FAILED for item in items),
        }
        for key, value in counts.items():
            self._metrics[key].set_value(value)


class _Metric(QWidget):
    def __init__(self, label: str, icon_name: str | None, color: str) -> None:
        super().__init__()
        self._value = QLabel("0")
        self._value.setObjectName("MetricValue")
        self._value.setStyleSheet(f"color: {color};")
        self._label = QLabel(label)
        self._label.setObjectName("Caption")

        value_row = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.setSpacing(7)
        if icon_name:
            icon = QLabel()
            icon.setPixmap(line_icon(icon_name, color, 17).pixmap(17, 17))
            icon.setFixedSize(18, 18)
            value_row.addWidget(icon)
        value_row.addWidget(self._value)
        value_row.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(1)
        layout.addLayout(value_row)
        layout.addWidget(self._label)

    def set_value(self, value: int) -> None:
        self._value.setText(str(value))
        self.setAccessibleName(f"{self._label.text()}: {value}")
