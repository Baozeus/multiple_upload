"""Icon + text status indicator; color is never the only signal."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from udm10.client.ui.icons import line_icon


class StatusBadge(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._icon = QLabel()
        self._icon.setFixedSize(20, 20)
        self._label = QLabel()
        self._label.setStyleSheet("font-weight: 600;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._icon)
        layout.addWidget(self._label)
        layout.addStretch()

    def set_status(self, *, text: str, icon_name: str, color: str) -> None:
        self._icon.setPixmap(line_icon(icon_name, color, 18).pixmap(18, 18))
        self._label.setText(text)
        self._label.setStyleSheet(f"font-weight: 600; color: {color};")
        self.setAccessibleName(text)
