"""Upload progress with explicit percentage text."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget


class UploadProgressBar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setTextVisible(False)
        self._percent = QLabel("0%")
        self._percent.setMinimumWidth(40)
        self._percent.setStyleSheet("font-weight: 600;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._bar, 1)
        layout.addWidget(self._percent)

    def set_progress(self, value: int, *, active: bool = True) -> None:
        value = min(100, max(0, int(value)))
        self._bar.setValue(value)
        self._bar.setEnabled(active)
        self._percent.setText(f"{value}%" if active or value else "—")
        self.setAccessibleName(f"Tiến trình {value} phần trăm" if active else "Chưa bắt đầu")
