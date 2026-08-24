"""Small authored line-icon system rendered from SVG path data."""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


_PATHS = {
    "upload": '<path d="M12 15V4m0 0L7.5 8.5M12 4l4.5 4.5M5 14.5V20h14v-5.5"/>',
    "history": '<path d="M4.8 8A8 8 0 1 1 4 12M4.8 8H1.5m3.3 0V4.7M12 7.5V12l3 2"/>',
    "connection": '<path d="M8.5 15.5l-2 2a3.5 3.5 0 0 1-5-5l3-3a3.5 3.5 0 0 1 5 0M15.5 8.5l2-2a3.5 3.5 0 0 1 5 5l-3 3a3.5 3.5 0 0 1-5 0M8 16l8-8"/>',
    "offline": '<path d="M8.5 15.5l-2 2a3.5 3.5 0 0 1-5-5l2-2M15.5 8.5l2-2a3.5 3.5 0 0 1 5 5l-2 2M9 15l6-6M3 3l18 18"/>',
    "file": '<path d="M6 2.5h8l4 4V21.5H6zM14 2.5v5h4M9 13h6M9 17h5"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "check": '<circle cx="12" cy="12" r="8.5"/><path d="M8 12.2l2.6 2.6L16.5 9"/>',
    "error": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5v5.3M12 16.4h.01"/>',
    "warning": '<path d="M12 3L2.8 20h18.4zM12 8.5v5M12 17h.01"/>',
    "retry": '<path d="M20 7v5h-5M4 17v-5h5M6.1 8.5A7 7 0 0 1 18.5 7M17.9 15.5A7 7 0 0 1 5.5 17"/>',
    "trash": '<path d="M4 6.5h16M9 3.5h6l1 3H8zM7 6.5l1 14h8l1-14M10 10v7M14 10v7"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18"/>',
    "folder": '<path d="M3 6.5h7l2 2h9v10H3z"/>',
}


@lru_cache(maxsize=128)
def line_icon(name: str, color: str = "#52606D", size: int = 20) -> QIcon:
    path = _PATHS.get(name, _PATHS["file"])
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{path}</svg>'''
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)
