"""Keyboard-friendly real file drag-and-drop target."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from udm10.client.ui.icons import line_icon
from udm10.client.ui.theme import COLORS


class DropZone(QFrame):
    files_selected = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setProperty("dragActive", False)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumHeight(128)
        self.setAccessibleName("Chọn hoặc thả nhiều tệp để tải lên")

        self._icon = QLabel()
        self._icon.setPixmap(line_icon("upload", COLORS["accent"], 30).pixmap(30, 30))
        self._icon.setFixedSize(34, 34)
        self._title = QLabel("Kéo và thả tệp vào đây")
        self._title.setObjectName("SectionTitle")
        self._note = QLabel(
            "Có thể chọn nhiều tệp cùng lúc • Giới hạn theo cấu hình máy chủ"
        )
        self._note.setObjectName("MutedText")
        self._note.setWordWrap(True)
        self._choose = QPushButton("Chọn tệp")
        self._choose.setObjectName("PrimaryButton")
        self._choose.setIcon(line_icon("folder", "#FFFFFF", 18))
        self._choose.clicked.connect(self.choose_files)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)
        text_layout.addWidget(self._title)
        text_layout.addWidget(self._note)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(16)
        layout.addWidget(self._icon)
        layout.addLayout(text_layout, 1)
        layout.addWidget(self._choose)

    def choose_files(self) -> None:
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            "Chọn tệp để tải lên",
            "",
            "Tất cả tệp (*)",
        )
        if filenames:
            self.files_selected.emit([Path(name) for name in filenames])

    def set_drag_active(self, active: bool) -> None:
        self.setProperty("dragActive", active)
        self._title.setText(
            "Thả tệp để thêm vào hàng đợi" if active else "Kéo và thả tệp vào đây"
        )
        self._icon.setPixmap(
            line_icon("upload", COLORS["accent"], 34 if active else 30).pixmap(
                34 if active else 30, 34 if active else 30
            )
        )
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        if _local_files(event.mimeData().urls()):
            event.acceptProposedAction()
            self.set_drag_active(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:  # noqa: N802
        self.set_drag_active(False)
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        files = _local_files(event.mimeData().urls())
        self.set_drag_active(False)
        if files:
            event.acceptProposedAction()
            self.files_selected.emit(files)
        else:
            event.ignore()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and not self._choose.geometry().contains(event.position().toPoint()):
            self.choose_files()
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.choose_files()
            event.accept()
            return
        super().keyPressEvent(event)


def _local_files(urls) -> list[Path]:
    files: list[Path] = []
    for url in urls:
        if not url.isLocalFile():
            continue
        path = Path(url.toLocalFile())
        if path.is_file():
            files.append(path)
    return files
