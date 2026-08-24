# THESIS: Một bàn chuyển tệp liên tục, từ chối dashboard nhiều card và cloud-gradient.
# OWN-WORLD: Cool-neutral canvas, white work surface, cobalt active rail, 1px separators, line icons.
# STORY: Chọn tệp, đọc trạng thái từng row, xử lý lỗi/trùng tên, rồi kiểm chứng trong Lịch sử.
# FIRST VIEWPORT: Top nav 56px; header + drop zone; summary strip; queue với tối thiểu 3 row ở 1366x768.
# FORM: Transfer Desk, grounded direction 7, seed 2ddf9409.
# FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, and DESIGN.md

"""Production desktop shell composing the upload and history workspaces."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QMainWindow, QStackedWidget, QToolButton, QVBoxLayout, QWidget

from udm10.client.models.history import HistoryEntry
from udm10.client.models.upload import UploadItem
from udm10.client.ui.history_view import HistoryView
from udm10.client.ui.icons import line_icon
from udm10.client.ui.theme import COLORS, build_stylesheet
from udm10.client.ui.upload_view import UploadView
from udm10.client.widgets.connection_status import ConnectionStatus, OfflineBanner


class MainWindow(QMainWindow):
    navigation_changed = Signal(str)
    retry_connection_requested = Signal()

    def __init__(self, server_host: str, server_port: int) -> None:
        super().__init__()
        self.setWindowTitle("UDM_10 - Multiple Upload")
        self.setMinimumSize(960, 640)
        self.resize(1366, 768)
        self.setStyleSheet(build_stylesheet())

        self.upload_view = UploadView()
        self.history_view = HistoryView()
        self._pages = QStackedWidget()
        self._pages.addWidget(self.upload_view)
        self._pages.addWidget(self.history_view)

        self.connection_status = ConnectionStatus()
        self.connection_status.setToolTip(f"Máy chủ: {server_host}:{server_port}")
        self.offline_banner = OfflineBanner()
        self.offline_banner.setVisible(False)
        self.offline_banner.retry_requested.connect(self.retry_connection_requested)

        nav = self._build_navigation()
        root = QWidget()
        root.setObjectName("AppRoot")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(nav)
        layout.addWidget(self.offline_banner)
        layout.addWidget(self._pages, 1)
        self.setCentralWidget(root)

        self.history_view.upload_navigation_requested.connect(lambda: self.set_page("upload"))
        self.set_page("upload")

    def set_page(self, page: str) -> None:
        is_upload = page == "upload"
        self._pages.setCurrentWidget(self.upload_view if is_upload else self.history_view)
        self._set_nav_active(self._upload_nav, is_upload)
        self._set_nav_active(self._history_nav, not is_upload)
        self.navigation_changed.emit(page)

    def set_online(self, online: bool) -> None:
        self.connection_status.set_online(online)
        self.offline_banner.setVisible(not online)
        self.offline_banner.set_retrying(False)

    def set_reconnecting(self, reconnecting: bool) -> None:
        """Expose retry presentation without leaking child widgets to controllers."""
        self.offline_banner.set_retrying(reconnecting)

    def set_uploads(self, items: Sequence[UploadItem]) -> None:
        self.upload_view.set_items(items)

    def set_history(self, entries: Sequence[HistoryEntry]) -> None:
        self.history_view.set_entries(entries)

    def set_history_loading(self, loading: bool) -> None:
        self.history_view.set_loading(loading)

    def _build_navigation(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("TopNavigation")
        bar.setFixedHeight(56)
        # Keep an explicit Python reference: native ownership alone is not enough
        # to guarantee wrapper lifetime across repeated stacked-page updates.
        self._brand = QToolButton()
        self._brand.setObjectName("BrandButton")
        self._brand.setText("UDM_10")
        self._brand.setIcon(line_icon("upload", COLORS["accent"], 20))
        self._brand.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._brand.setAutoRaise(True)
        self._brand.clicked.connect(lambda: self.set_page("upload"))

        self._upload_nav = self._nav_button("Tải tệp", "upload")
        self._history_nav = self._nav_button("Lịch sử", "history")
        self._upload_nav.clicked.connect(lambda: self.set_page("upload"))
        self._history_nav.clicked.connect(lambda: self.set_page("history"))
        group = QButtonGroup(self)
        group.setExclusive(True)
        group.addButton(self._upload_nav)
        group.addButton(self._history_nav)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(4)
        layout.addWidget(self._brand)
        layout.addSpacing(20)
        layout.addWidget(self._upload_nav)
        layout.addWidget(self._history_nav)
        layout.addStretch()
        layout.addWidget(self.connection_status)
        return bar

    @staticmethod
    def _nav_button(text: str, icon_name: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName("NavButton")
        button.setText(text)
        button.setIcon(line_icon(icon_name, COLORS["muted"], 18))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setCheckable(True)
        button.setAccessibleName(f"Mở trang {text}")
        return button

    @staticmethod
    def _set_nav_active(button: QToolButton, active: bool) -> None:
        button.setChecked(active)
        button.setProperty("active", active)
        color = COLORS["accent"] if active else COLORS["muted"]
        icon_name = "upload" if button.text() == "Tải tệp" else "history"
        button.setIcon(line_icon(icon_name, color, 18))
        button.style().unpolish(button)
        button.style().polish(button)
