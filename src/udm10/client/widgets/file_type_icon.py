"""Compact authored document icon with an extension label."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from udm10.client.ui.theme import COLORS


class FileTypeIcon(QWidget):
    def __init__(self, filename: str = "", parent=None) -> None:
        super().__init__(parent)
        self._extension = _short_extension(filename)
        self.setFixedSize(36, 40)

    def set_filename(self, filename: str) -> None:
        self._extension = _short_extension(filename)
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(36, 40)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        outline = QColor(COLORS["border_strong"])
        fill = QColor(COLORS["surface"])
        path = QPainterPath()
        path.moveTo(6, 2)
        path.lineTo(24, 2)
        path.lineTo(32, 10)
        path.lineTo(32, 37)
        path.lineTo(6, 37)
        path.closeSubpath()
        painter.fillPath(path, fill)
        painter.setPen(QPen(outline, 1.3))
        painter.drawPath(path)
        painter.drawLine(24, 2, 24, 10)
        painter.drawLine(24, 10, 32, 10)

        label_rect = QRectF(3, 21, 32, 13)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(COLORS["accent_subtle"]))
        painter.drawRoundedRect(label_rect, 3, 3)
        painter.setPen(QColor(COLORS["accent"]))
        font = QFont(self.font())
        font.setPixelSize(8)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, self._extension)
        painter.end()


def _short_extension(filename: str) -> str:
    extension = Path(filename).suffix.removeprefix(".").upper()
    if not extension:
        return "FILE"
    return extension[:4]
