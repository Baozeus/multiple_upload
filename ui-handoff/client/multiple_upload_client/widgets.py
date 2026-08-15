"""Reusable, accessible widgets for the Multiple Upload desktop client."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QFontMetrics,
    QIcon,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .history import HistoryRecord
from .models import UploadItem, UploadStatus, format_file_size


def _draw_line_icon(painter: QPainter, name: str, size: int, color: str) -> None:
    """Draw the small line-icon system used throughout the native client."""

    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(
        QPen(
            QColor(color),
            max(1.7, size / 11),
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
    )
    painter.setBrush(Qt.BrushStyle.NoBrush)
    scale = size / 24

    def point(x: float, y: float) -> QPointF:
        return QPointF(x * scale, y * scale)

    if name in {"upload", "brand"}:
        painter.drawLine(point(12, 17), point(12, 5))
        painter.drawLine(point(8, 9), point(12, 5))
        painter.drawLine(point(16, 9), point(12, 5))
        painter.drawLine(point(4, 16), point(4, 20))
        painter.drawLine(point(4, 20), point(20, 20))
        painter.drawLine(point(20, 20), point(20, 16))
    elif name == "history":
        painter.drawRoundedRect(QRectF(5 * scale, 3 * scale, 14 * scale, 18 * scale), 2, 2)
        painter.drawLine(point(8, 8), point(16, 8))
        painter.drawLine(point(8, 12), point(16, 12))
        painter.drawLine(point(8, 16), point(13, 16))
    elif name == "refresh":
        path = QPainterPath(point(18, 8))
        path.cubicTo(point(15, 3), point(7, 3), point(4, 9))
        path.cubicTo(point(1, 15), point(7, 21), point(14, 19))
        painter.drawPath(path)
        painter.drawLine(point(18, 8), point(18, 3))
        painter.drawLine(point(18, 8), point(13, 8))
    elif name == "clock":
        painter.drawEllipse(QRectF(3 * scale, 3 * scale, 18 * scale, 18 * scale))
        painter.drawLine(point(12, 7), point(12, 12))
        painter.drawLine(point(12, 12), point(16, 14))
    elif name == "trash":
        painter.drawRoundedRect(QRectF(6 * scale, 7 * scale, 12 * scale, 14 * scale), 1, 1)
        painter.drawLine(point(4, 7), point(20, 7))
        painter.drawLine(point(9, 4), point(15, 4))
        painter.drawLine(point(10, 10), point(10, 18))
        painter.drawLine(point(14, 10), point(14, 18))
    elif name == "search":
        painter.drawEllipse(QRectF(4 * scale, 4 * scale, 11 * scale, 11 * scale))
        painter.drawLine(point(14, 14), point(20, 20))
    elif name == "check":
        painter.drawEllipse(QRectF(3 * scale, 3 * scale, 18 * scale, 18 * scale))
        painter.drawLine(point(7, 12), point(10.5, 15.5))
        painter.drawLine(point(10.5, 15.5), point(17, 8.5))
    elif name == "warning":
        triangle = QPainterPath(point(12, 3))
        triangle.lineTo(point(21, 20))
        triangle.lineTo(point(3, 20))
        triangle.closeSubpath()
        painter.drawPath(triangle)
        painter.drawLine(point(12, 8), point(12, 14))
        painter.drawPoint(point(12, 17))


def make_icon(name: str, color: str = "#38506A", size: int = 20) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    _draw_line_icon(painter, name, size, color)
    painter.end()
    return QIcon(pixmap)


class LineIcon(QWidget):
    def __init__(
        self,
        name: str,
        color: str = "#1769E0",
        size: int = 28,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.name = name
        self.color = color
        self.icon_size = size
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:  # noqa: ANN001
        del event
        painter = QPainter(self)
        _draw_line_icon(painter, self.name, self.icon_size, self.color)


class BrandMark(QWidget):
    """Compact vector mark combining multiple documents with an upload arrow."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.setAccessibleName("Logo Multiple Upload")

    def paintEvent(self, event) -> None:  # noqa: ANN001
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#EAF2FE"))
        painter.drawRoundedRect(QRectF(0, 0, 36, 36), 9, 9)

        pen = QPen(QColor("#1769E0"), 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        back = QPainterPath(QPointF(12, 8))
        back.lineTo(23, 8)
        back.lineTo(28, 13)
        back.lineTo(28, 25)
        painter.drawPath(back)

        front = QPainterPath(QPointF(8, 12))
        front.lineTo(19, 12)
        front.lineTo(24, 17)
        front.lineTo(24, 29)
        front.lineTo(8, 29)
        front.closeSubpath()
        painter.drawPath(front)
        painter.drawLine(QPointF(19, 12), QPointF(19, 17))
        painter.drawLine(QPointF(19, 17), QPointF(24, 17))

        painter.drawLine(QPointF(16, 26), QPointF(16, 19))
        painter.drawLine(QPointF(13, 22), QPointF(16, 19))
        painter.drawLine(QPointF(19, 22), QPointF(16, 19))


class FileTypeIcon(QWidget):
    _COLORS = {
        "pdf": "#D93025",
        "csv": "#188038",
        "xlsx": "#188038",
        "xls": "#188038",
        "doc": "#1769E0",
        "docx": "#1769E0",
        "zip": "#C57B08",
        "rar": "#C57B08",
        "mp4": "#7B4CC2",
        "mov": "#7B4CC2",
    }

    def __init__(self, extension: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.extension = extension.lower()
        self.setFixedSize(34, 40)

    def set_extension(self, extension: str) -> None:
        self.extension = extension.lower()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: ANN001
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(self._COLORS.get(self.extension, "#5F6B7A"))
        pen = QPen(color, 1.7)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QColor(color.red(), color.green(), color.blue(), 13))
        path = QPainterPath()
        path.moveTo(7, 3)
        path.lineTo(21, 3)
        path.lineTo(28, 10)
        path.lineTo(28, 36)
        path.lineTo(7, 36)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(21, 3, 21, 10)
        painter.drawLine(21, 10, 28, 10)
        painter.setPen(color)
        font = QFont("Segoe UI", 6)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(
            QRectF(7, 17, 21, 12),
            Qt.AlignmentFlag.AlignCenter,
            self.extension[:4].upper(),
        )


class ConnectionBadge(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("connectionBadge")
        self.setProperty("connectionState", "neutral")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(9, 5, 10, 5)
        layout.setSpacing(7)
        self.dot = QLabel()
        self.dot.setObjectName("connectionDot")
        self.dot.setFixedSize(8, 8)
        self.label = QLabel("Đang kiểm tra API")
        self.label.setObjectName("connectionText")
        layout.addWidget(self.dot)
        layout.addWidget(self.label)

    def set_mode(self, message: str) -> None:
        lowered = message.lower()
        if "hoạt động" in lowered:
            state, text = "success", "API đang hoạt động"
        elif "api:" in lowered:
            state, text = "configured", "API đã cấu hình"
        elif "fallback" in lowered or "mô phỏng" in lowered:
            state, text = "warning", "Mô phỏng cục bộ"
        else:
            state, text = "neutral", message
        self.label.setText(text)
        self.setToolTip(message)
        self.setProperty("connectionState", state)
        self.style().unpolish(self)
        self.style().polish(self)
        self.dot.style().unpolish(self.dot)
        self.dot.style().polish(self.dot)


class StatusBadge(QFrame):
    _ICON_AND_COLOR = {
        "waiting": ("clock", "#945A00"),
        "uploading": ("upload", "#0B62CE"),
        "completed": ("check", "#137A49"),
        "error": ("warning", "#B3261E"),
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statusBadge")
        self.setFixedSize(108, 30)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(7, 0, 7, 0)
        layout.setSpacing(5)
        self.icon = LineIcon("clock", "#945A00", 14)
        self.label = QLabel("Chờ")
        self.label.setObjectName("statusText")
        layout.addWidget(self.icon)
        layout.addWidget(self.label)
        layout.addStretch()
        self.set_status("Chờ", "waiting")

    def set_status(self, text: str, key: str) -> None:
        icon_name, color = self._ICON_AND_COLOR[key]
        self.icon.name = icon_name
        self.icon.color = color
        self.icon.update()
        self.label.setText(text)
        self.label.setStyleSheet(f"color: {color};")
        self.setProperty("status", key)
        self.style().unpolish(self)
        self.style().polish(self)


class DropZone(QFrame):
    files_dropped = Signal(list)
    choose_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setProperty("dragActive", False)
        self.setMinimumHeight(104)
        self.setMaximumHeight(124)
        self.setAccessibleName("Khu vực kéo thả tệp")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 18, 22, 18)
        layout.setSpacing(16)
        icon_wrap = QFrame()
        icon_wrap.setObjectName("dropIconWrap")
        icon_wrap.setFixedSize(48, 48)
        icon_layout = QHBoxLayout(icon_wrap)
        icon_layout.setContentsMargins(10, 10, 10, 10)
        icon_layout.addWidget(LineIcon("upload", "#1769E0", 28))

        copy = QVBoxLayout()
        copy.setSpacing(3)
        self.title = QLabel("Kéo và thả tệp vào đây")
        self.title.setObjectName("dropTitle")
        note = QLabel("Hoặc chọn từ máy tính · Tối đa 6 tệp tải lên cùng lúc")
        note.setObjectName("muted")
        copy.addWidget(self.title)
        copy.addWidget(note)

        choose_button = QPushButton("Chọn tệp")
        choose_button.setObjectName("primaryButton")
        choose_button.setIcon(make_icon("upload", "#FFFFFF", 18))
        choose_button.setIconSize(QSize(18, 18))
        choose_button.setCursor(Qt.CursorShape.PointingHandCursor)
        choose_button.setToolTip("Chọn một hoặc nhiều tệp (Ctrl+U)")
        choose_button.clicked.connect(self.choose_requested)

        layout.addWidget(icon_wrap)
        layout.addLayout(copy)
        layout.addStretch()
        layout.addWidget(choose_button)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() and any(
            url.isLocalFile() for url in event.mimeData().urls()
        ):
            event.acceptProposedAction()
            self._set_drag_active(True)

    def dragLeaveEvent(self, event) -> None:  # noqa: ANN001
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        self._set_drag_active(False)
        event.acceptProposedAction()
        self.files_dropped.emit(paths)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.choose_requested.emit()
        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space}:
            self.choose_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def _set_drag_active(self, active: bool) -> None:
        self.setProperty("dragActive", active)
        self.title.setText(
            "Thả tệp để thêm vào hàng đợi" if active else "Kéo và thả tệp vào đây"
        )
        self.style().unpolish(self)
        self.style().polish(self)


class StatMetric(QWidget):
    def __init__(
        self,
        label: str,
        tone: str = "neutral",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(1)
        self.value = QLabel("0")
        self.value.setObjectName("metricValue")
        self.value.setProperty("tone", tone)
        title = QLabel(label)
        title.setObjectName("metricLabel")
        layout.addWidget(title)
        layout.addWidget(self.value)

    def set_value(self, value: int | str) -> None:
        self.value.setText(str(value))


class UploadTableHeader(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("tableHeader")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 12, 0)
        layout.setSpacing(12)
        icon_space = QWidget()
        icon_space.setFixedWidth(34)
        layout.addWidget(icon_space)
        self._add(layout, "Tên tệp", 210, 3)
        self._add(layout, "Kích thước", 90)
        self._add(layout, "Tiến độ", 180, 3)
        self._add(layout, "Tốc độ", 90)
        self._add(layout, "Trạng thái", 108)
        self._add(layout, "Thời gian", 88)
        self._add(layout, "Thao tác", 84)

    @staticmethod
    def _add(layout: QHBoxLayout, text: str, width: int, stretch: int = 0) -> None:
        label = QLabel(text)
        label.setObjectName("columnLabel")
        if stretch:
            label.setMinimumWidth(width)
            layout.addWidget(label, stretch)
        else:
            label.setFixedWidth(width)
            layout.addWidget(label)


class FileRow(QFrame):
    remove_requested = Signal(str)
    action_requested = Signal(str)

    def __init__(self, item: UploadItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.item_id = item.id
        self.current_action = ""
        self.setObjectName("fileRow")
        self.setMinimumHeight(68)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(14, 8, 12, 8)
        outer.setSpacing(12)
        self.file_icon = FileTypeIcon(item.extension)

        identity_widget = QWidget()
        identity = QVBoxLayout(identity_widget)
        identity.setContentsMargins(0, 0, 0, 0)
        identity.setSpacing(2)
        self.name_label = QLabel()
        self.name_label.setObjectName("fileName")
        self.name_label.setMinimumWidth(210)
        self.name_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.detail_label = QLabel()
        self.detail_label.setObjectName("rowDetail")
        identity.addWidget(self.name_label)
        identity.addWidget(self.detail_label)

        self.size_label = QLabel()
        self.size_label.setObjectName("dataCell")
        self.size_label.setFixedWidth(90)

        progress_widget = QWidget()
        progress_layout = QHBoxLayout(progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(9)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        self.progress.setMinimumWidth(130)
        self.percent_label = QLabel()
        self.percent_label.setObjectName("percentCell")
        self.percent_label.setFixedWidth(38)
        self.percent_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        progress_layout.addWidget(self.progress, 1)
        progress_layout.addWidget(self.percent_label)

        self.speed_label = QLabel()
        self.speed_label.setObjectName("dataCell")
        self.speed_label.setFixedWidth(90)
        self.status_label = StatusBadge()
        self.time_label = QLabel()
        self.time_label.setObjectName("dataCell")
        self.time_label.setFixedWidth(88)

        self.action_button = QPushButton()
        self.action_button.setObjectName("rowActionButton")
        self.action_button.setFixedWidth(84)
        self.action_button.clicked.connect(self._dispatch_action)

        outer.addWidget(self.file_icon)
        outer.addWidget(identity_widget, 3)
        outer.addWidget(self.size_label)
        outer.addWidget(progress_widget, 3)
        outer.addWidget(self.speed_label)
        outer.addWidget(self.status_label)
        outer.addWidget(self.time_label)
        outer.addWidget(self.action_button)
        self.update_item(item)

    def _dispatch_action(self) -> None:
        if self.current_action == "remove":
            self.remove_requested.emit(self.item_id)
        elif self.current_action:
            self.action_requested.emit(self.item_id)

    def update_time(self, item: UploadItem) -> None:
        self.time_label.setText(item.elapsed_text)

    def update_item(self, item: UploadItem) -> None:
        self.file_icon.set_extension(item.extension)
        self.name_label.setText(
            QFontMetrics(self.name_label.font()).elidedText(
                item.name, Qt.TextElideMode.ElideMiddle, 300
            )
        )
        self.name_label.setToolTip(str(item.path))
        self.size_label.setText(format_file_size(item.size))
        self.speed_label.setText(item.speed)
        self.percent_label.setText(f"{item.progress}%")
        self.progress.setValue(item.progress)
        self.update_time(item)

        status_key = {
            UploadStatus.WAITING: "waiting",
            UploadStatus.UPLOADING: "uploading",
            UploadStatus.COMPLETED: "completed",
            UploadStatus.ERROR: "error",
        }[item.status]
        self.status_label.set_status(item.status.value, status_key)
        self.progress.setProperty("progressState", status_key)
        for widget in (self.status_label, self.progress):
            widget.style().unpolish(widget)
            widget.style().polish(widget)

        show_detail = item.status is UploadStatus.ERROR or item.conflict_pending
        self.detail_label.setVisible(show_detail)
        if show_detail:
            self.detail_label.setText(
                QFontMetrics(self.detail_label.font()).elidedText(
                    item.detail, Qt.TextElideMode.ElideRight, 300
                )
            )
            self.detail_label.setToolTip(item.detail)

        if item.conflict_pending:
            self.current_action = "conflict"
            self.action_button.setText("Xử lý")
            self.action_button.setIcon(make_icon("warning", "#1769E0", 15))
            self.action_button.setToolTip("Chọn cách xử lý tệp trùng tên")
            self.action_button.setVisible(True)
        elif item.status is UploadStatus.ERROR:
            self.current_action = "retry"
            self.action_button.setText("Thử lại")
            self.action_button.setIcon(make_icon("refresh", "#1769E0", 15))
            self.action_button.setToolTip(f"Thử tải lại: {item.detail}")
            self.action_button.setVisible(True)
        elif item.status is UploadStatus.UPLOADING:
            self.current_action = ""
            self.action_button.setIcon(QIcon())
            self.action_button.setVisible(False)
        else:
            self.current_action = "remove"
            self.action_button.setText("Xóa")
            self.action_button.setIcon(make_icon("trash", "#1769E0", 15))
            self.action_button.setToolTip("Xóa tệp khỏi danh sách")
            self.action_button.setVisible(True)


class HistoryTableHeader(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("tableHeader")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 12, 0)
        layout.setSpacing(12)
        icon_space = QWidget()
        icon_space.setFixedWidth(34)
        layout.addWidget(icon_space)
        UploadTableHeader._add(layout, "Tên tệp", 240, 4)
        UploadTableHeader._add(layout, "Kích thước", 100)
        UploadTableHeader._add(layout, "Thời điểm tải", 150)
        UploadTableHeader._add(layout, "Trạng thái", 110)
        UploadTableHeader._add(layout, "Xử lý tên trùng", 130)
        UploadTableHeader._add(layout, "Nguồn", 130)


class HistoryRow(QFrame):
    def __init__(self, record: HistoryRecord, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.record = record
        self.setObjectName("historyRow")
        self.setMinimumHeight(62)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 7, 12, 7)
        layout.setSpacing(12)
        icon = FileTypeIcon(record.file_type)

        identity = QWidget()
        identity_layout = QVBoxLayout(identity)
        identity_layout.setContentsMargins(0, 0, 0, 0)
        identity_layout.setSpacing(1)
        name = QLabel(record.name)
        name.setObjectName("fileName")
        name.setToolTip(record.name)
        kind = QLabel(record.file_type)
        kind.setObjectName("rowDetail")
        identity_layout.addWidget(name)
        identity_layout.addWidget(kind)

        size = QLabel(format_file_size(record.size))
        size.setObjectName("dataCell")
        size.setFixedWidth(100)
        uploaded = QLabel(record.uploaded_at_display)
        uploaded.setObjectName("dataCell")
        uploaded.setFixedWidth(150)
        status = StatusBadge()
        status_key = {
            UploadStatus.COMPLETED.value: "completed",
            UploadStatus.ERROR.value: "error",
            "Bỏ qua": "waiting",
        }.get(record.status, "waiting")
        status.set_status(record.status, status_key)
        conflict = QLabel(record.conflict_result)
        conflict.setObjectName("dataCell")
        conflict.setFixedWidth(130)
        source = QLabel(record.source)
        source.setObjectName("dataCell")
        source.setFixedWidth(130)

        layout.addWidget(icon)
        layout.addWidget(identity, 4)
        layout.addWidget(size)
        layout.addWidget(uploaded)
        layout.addWidget(status)
        layout.addWidget(conflict)
        layout.addWidget(source)
