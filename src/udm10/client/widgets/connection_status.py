"""Connection indicator and persistent offline banner."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from udm10.client.ui.icons import line_icon
from udm10.client.ui.theme import COLORS


class ConnectionStatus(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._icon = QLabel()
        self._icon.setFixedSize(20, 20)
        self._label = QLabel()
        self._label.setStyleSheet("font-weight: 600;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)
        layout.addWidget(self._icon)
        layout.addWidget(self._label)
        self.set_online(True)

    def set_online(self, online: bool) -> None:
        icon_name = "connection" if online else "offline"
        color = COLORS["success"] if online else COLORS["offline"]
        text = "Đã kết nối" if online else "Mất kết nối"
        self._icon.setPixmap(line_icon(icon_name, color, 18).pixmap(18, 18))
        self._label.setText(text)
        self._label.setStyleSheet(f"font-weight: 600; color: {color};")
        self.setAccessibleName(f"Trạng thái máy chủ: {text}")


class OfflineBanner(QFrame):
    retry_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("OfflineBanner")
        icon = QLabel()
        icon.setPixmap(line_icon("offline", COLORS["offline"], 18).pixmap(18, 18))
        icon.setFixedSize(20, 20)
        text = QLabel(
            "Mất kết nối máy chủ. Tệp đang chờ vẫn được giữ lại; "
            "các tệp đang tải có thể cần thử lại."
        )
        text.setWordWrap(True)
        text.setStyleSheet(f"color: {COLORS['offline']}; font-weight: 600;")
        self._button = QPushButton("Thử kết nối")
        self._button.clicked.connect(self.retry_requested)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 10, 24, 10)
        layout.setSpacing(10)
        layout.addWidget(icon)
        layout.addWidget(text, 1)
        layout.addWidget(self._button)
        self.setAccessibleName(text.text())

    def set_retrying(self, retrying: bool) -> None:
        self._button.setDisabled(retrying)
        self._button.setText("Đang kết nối…" if retrying else "Thử kết nối")
