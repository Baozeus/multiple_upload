"""Inline error/warning message with authored iconography."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from udm10.client.ui.icons import line_icon
from udm10.client.ui.theme import COLORS


class ErrorMessage(QFrame):
    def __init__(self, text: str = "", *, warning: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._warning = warning
        self.setObjectName("WarningMessage" if warning else "ErrorMessage")
        color = COLORS["warning"] if warning else COLORS["error"]
        icon_name = "warning" if warning else "error"

        icon = QLabel()
        icon.setPixmap(line_icon(icon_name, color, 18).pixmap(18, 18))
        icon.setFixedSize(20, 20)
        self._label = QLabel(text)
        self._label.setWordWrap(True)
        self._label.setStyleSheet(f"color: {color}; font-weight: 600;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(10)
        layout.addWidget(icon, 0)
        layout.addWidget(self._label, 1)
        self.setAccessibleName(text)

    def set_message(self, text: str) -> None:
        self._label.setText(text)
        self.setAccessibleName(text)
