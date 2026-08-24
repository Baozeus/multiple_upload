"""Reusable educational empty state for queue and history."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from udm10.client.ui.icons import line_icon
from udm10.client.ui.theme import COLORS


class EmptyState(QWidget):
    action_requested = Signal()

    def __init__(
        self,
        *,
        icon_name: str,
        title: str,
        description: str,
        action_text: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        icon = QLabel()
        icon.setPixmap(line_icon(icon_name, COLORS["muted"], 32).pixmap(32, 32))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        heading = QLabel(title)
        heading.setObjectName("SectionTitle")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body = QLabel(description)
        body.setObjectName("MutedText")
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.setMaximumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 28, 24, 28)
        layout.setSpacing(8)
        layout.addStretch()
        layout.addWidget(icon)
        layout.addWidget(heading)
        layout.addWidget(body)
        if action_text:
            action = QPushButton(action_text)
            action.clicked.connect(self.action_requested)
            action_row = QHBoxLayout()
            action_row.addStretch()
            action_row.addWidget(action)
            action_row.addStretch()
            layout.addSpacing(4)
            layout.addLayout(action_row)
        layout.addStretch()
