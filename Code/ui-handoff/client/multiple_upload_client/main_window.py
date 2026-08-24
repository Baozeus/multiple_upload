"""Compact Ledger main window for the standalone Multiple Upload client."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .config import ClientConfig
from .history import HistoryRecord, HistoryStore
from .models import UploadItem, UploadStatus
from .theme import APP_STYLESHEET
from .uploader import UploadCoordinator
from .widgets import (
    BrandMark,
    ConnectionBadge,
    DropZone,
    FileRow,
    HistoryRow,
    HistoryTableHeader,
    StatMetric,
    UploadTableHeader,
    make_icon,
)


class MainWindow(QMainWindow):
    def __init__(
        self,
        config: ClientConfig,
        history_store: HistoryStore | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Multiple Upload — UDM_10")
        self.setMinimumSize(1120, 700)
        self.resize(1366, 768)
        self.setStyleSheet(APP_STYLESHEET)
        self.rows: dict[str, FileRow] = {}
        self.history_store = history_store or HistoryStore()
        self.coordinator = UploadCoordinator(config, self)
        self._connection_mode_message = ""

        root = QWidget()
        root.setObjectName("appRoot")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(self._build_navigation())

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_upload_page())
        self.pages.addWidget(self._build_history_page())
        shell.addWidget(self.pages, 1)

        self.statusBar().showMessage("Sẵn sàng")
        self._connect_coordinator()
        self._install_shortcuts()
        self._refresh_summary()
        self._refresh_history()

        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.setInterval(1000)
        self.elapsed_timer.timeout.connect(self._refresh_elapsed_times)
        self.elapsed_timer.start()

    def _build_navigation(self) -> QFrame:
        rail = QFrame()
        rail.setObjectName("navRail")
        rail.setFixedWidth(202)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(14, 20, 14, 18)
        layout.setSpacing(8)

        brand = QFrame()
        brand.setObjectName("brandBlock")
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(4, 0, 2, 14)
        brand_layout.setSpacing(10)
        brand_layout.addWidget(BrandMark())
        brand_copy = QVBoxLayout()
        brand_copy.setSpacing(1)
        brand_copy.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        brand_name = QLabel("Multiple Upload")
        brand_name.setObjectName("brandName")
        brand_meta = QLabel("UDM_10")
        brand_meta.setObjectName("brandMeta")
        brand_copy.addWidget(brand_name)
        brand_copy.addWidget(brand_meta)
        brand_layout.addLayout(brand_copy)
        layout.addWidget(brand)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_upload = self._nav_button("Tải lên", "upload")
        self.nav_history = self._nav_button("Tệp đã tải", "history")
        self.nav_group.addButton(self.nav_upload, 0)
        self.nav_group.addButton(self.nav_history, 1)
        self.nav_upload.setChecked(True)
        self.nav_upload.clicked.connect(lambda: self._show_page(0))
        self.nav_history.clicked.connect(lambda: self._show_page(1))
        layout.addWidget(self.nav_upload)
        layout.addWidget(self.nav_history)
        layout.addStretch()
        return rail

    @staticmethod
    def _nav_button(text: str, icon_name: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("navButton")
        button.setCheckable(True)
        button.setIcon(make_icon(icon_name, "#38506A", 20))
        button.setIconSize(QSize(20, 20))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _build_upload_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 24, 30, 22)
        layout.setSpacing(16)
        header = self._page_header(
            "Tải lên nhiều tệp",
            "Thêm tệp và theo dõi từng tiến trình trong một hàng đợi rõ ràng.",
        )
        self.connection_badge = ConnectionBadge()
        header.addWidget(self.connection_badge, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(header)

        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self.coordinator.add_files)
        self.drop_zone.choose_requested.connect(self._choose_files)
        layout.addWidget(self.drop_zone)
        layout.addWidget(self._build_status_ledger())
        layout.addWidget(self._build_file_panel(), 1)
        return page

    def _page_header(self, title_text: str, subtitle_text: str) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(12)
        copy = QVBoxLayout()
        copy.setSpacing(3)
        title = QLabel(title_text)
        title.setObjectName("pageTitle")
        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("pageSubtitle")
        copy.addWidget(title)
        copy.addWidget(subtitle)
        layout.addLayout(copy)
        layout.addStretch()
        return layout

    def _build_status_ledger(self) -> QFrame:
        ledger = QFrame()
        ledger.setObjectName("statusLedger")
        ledger.setMinimumHeight(64)
        layout = QHBoxLayout(ledger)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        definitions = [
            ("Tổng số tệp", "Tổng", "neutral"),
            ("Đang tải", UploadStatus.UPLOADING.value, "uploading"),
            ("Đang chờ", UploadStatus.WAITING.value, "waiting"),
            ("Thành công", UploadStatus.COMPLETED.value, "completed"),
            ("Lỗi", UploadStatus.ERROR.value, "error"),
        ]
        self.stat_metrics: dict[str, StatMetric] = {}
        for index, (label, key, tone) in enumerate(definitions):
            metric = StatMetric(label, tone)
            self.stat_metrics[key] = metric
            layout.addWidget(metric, 1)
            if index < len(definitions) - 1:
                divider = QFrame()
                divider.setObjectName("metricDivider")
                divider.setFixedSize(1, 34)
                layout.addWidget(divider, alignment=Qt.AlignmentFlag.AlignVCenter)
        return ledger

    def _build_file_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("tablePanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(14, 10, 12, 10)
        toolbar_layout.setSpacing(8)
        title_group = QVBoxLayout()
        title_group.setSpacing(1)
        title = QLabel("Danh sách tải lên")
        title.setObjectName("sectionTitle")
        self.list_meta = QLabel("Chưa có tệp nào")
        self.list_meta.setObjectName("sectionMeta")
        title_group.addWidget(title)
        title_group.addWidget(self.list_meta)
        add_button = QPushButton("Tải thêm tệp")
        add_button.setObjectName("quietButton")
        add_button.clicked.connect(self._choose_files)
        self.clear_button = QPushButton("Xóa tất cả")
        self.clear_button.setObjectName("dangerButton")
        self.clear_button.clicked.connect(self._confirm_clear)
        toolbar_layout.addLayout(title_group)
        toolbar_layout.addStretch()
        conflict_label = QLabel("Khi trùng tên")
        conflict_label.setObjectName("sectionMeta")
        self.conflict_select = QComboBox()
        self.conflict_select.addItem("Đổi tên", "rename")
        self.conflict_select.addItem("Ghi đè", "overwrite")
        self.conflict_select.addItem("Bỏ qua", "skip")
        self.conflict_select.setAccessibleName("Cách xử lý khi tệp trùng tên")
        configured_policy = self.coordinator.config.conflict_policy
        configured_index = self.conflict_select.findData(configured_policy)
        self.conflict_select.setCurrentIndex(max(0, configured_index))
        self.conflict_select.currentIndexChanged.connect(
            self._change_conflict_policy
        )
        toolbar_layout.addWidget(conflict_label)
        toolbar_layout.addWidget(self.conflict_select)
        toolbar_layout.addWidget(add_button)
        toolbar_layout.addWidget(self.clear_button)
        panel_layout.addWidget(toolbar)
        panel_layout.addWidget(UploadTableHeader())

        self.empty_state = self._empty_state(
            "Chưa có tệp trong hàng đợi",
            "Kéo-thả vào vùng phía trên hoặc chọn tệp để bắt đầu.",
        )
        panel_layout.addWidget(self.empty_state, 1)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_container = QWidget()
        self.list_container.setObjectName("tableBody")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(0)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_container)
        self.scroll.setVisible(False)
        panel_layout.addWidget(self.scroll, 1)

        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(14, 8, 12, 8)
        self.footer_summary = QLabel()
        self.footer_summary.setObjectName("sectionMeta")
        footer_note = QLabel(
            f"FIFO · tối đa {self.coordinator.queue.max_concurrent} tệp cùng lúc"
        )
        footer_note.setObjectName("sectionMeta")
        footer_layout.addWidget(self.footer_summary)
        footer_layout.addStretch()
        footer_layout.addWidget(footer_note)
        panel_layout.addWidget(footer)
        return panel

    def _build_history_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 24, 30, 22)
        layout.setSpacing(16)
        layout.addLayout(
            self._page_header(
                "Tệp đã tải",
                "Tra cứu kết quả upload đã được ghi nhận trên máy tính này.",
            )
        )

        notice = QFrame()
        notice.setObjectName("infoStrip")
        notice_layout = QHBoxLayout(notice)
        notice_layout.setContentsMargins(13, 9, 13, 9)
        notice_text = QLabel(
            "Lịch sử đang được lưu cục bộ vì Server chưa có endpoint lịch sử. "
            "Dữ liệu không tự đồng bộ giữa các máy."
        )
        notice_text.setObjectName("infoText")
        notice_text.setToolTip(str(self.history_store.path))
        notice_layout.addWidget(notice_text)
        layout.addWidget(notice)

        tools = QHBoxLayout()
        tools.setSpacing(9)
        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText("Tìm theo tên tệp")
        self.history_search.setClearButtonEnabled(True)
        self.history_search.setAccessibleName("Tìm kiếm lịch sử theo tên tệp")
        self.history_search.textChanged.connect(self._refresh_history)
        self.history_filter = QComboBox()
        self.history_filter.addItems(["Tất cả trạng thái", "Hoàn tất", "Lỗi", "Bỏ qua"])
        self.history_filter.setFixedWidth(172)
        self.history_filter.currentTextChanged.connect(self._refresh_history)
        refresh_button = QPushButton("Làm mới")
        refresh_button.setIcon(make_icon("refresh", "#38506A", 18))
        refresh_button.clicked.connect(self._refresh_history)
        tools.addWidget(self.history_search, 1)
        tools.addWidget(self.history_filter)
        tools.addWidget(refresh_button)
        layout.addLayout(tools)

        panel = QFrame()
        panel.setObjectName("tablePanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 10, 12, 10)
        title = QLabel("Lịch sử upload")
        title.setObjectName("sectionTitle")
        self.history_meta = QLabel("0 bản ghi")
        self.history_meta.setObjectName("sectionMeta")
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.history_meta)
        panel_layout.addWidget(header)
        panel_layout.addWidget(HistoryTableHeader())

        self.history_empty = self._empty_state(
            "Chưa có lịch sử upload",
            "Các tệp hoàn tất, lỗi hoặc bị bỏ qua sẽ xuất hiện tại đây.",
        )
        panel_layout.addWidget(self.history_empty, 1)
        self.history_scroll = QScrollArea()
        self.history_scroll.setWidgetResizable(True)
        self.history_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.history_container = QWidget()
        self.history_container.setObjectName("tableBody")
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setContentsMargins(0, 0, 0, 0)
        self.history_layout.setSpacing(0)
        self.history_layout.addStretch()
        self.history_scroll.setWidget(self.history_container)
        self.history_scroll.setVisible(False)
        panel_layout.addWidget(self.history_scroll, 1)
        layout.addWidget(panel, 1)
        return page

    @staticmethod
    def _empty_state(title_text: str, detail_text: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("emptyState")
        frame.setMinimumHeight(130)
        layout = QVBoxLayout(frame)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(4)
        title = QLabel(title_text)
        title.setObjectName("emptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail = QLabel(detail_text)
        detail.setObjectName("muted")
        detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(detail)
        return frame

    def _connect_coordinator(self) -> None:
        self.coordinator.item_added.connect(self._add_row)
        self.coordinator.item_updated.connect(self._update_row)
        self.coordinator.item_removed.connect(self._remove_row)
        self.coordinator.queue_changed.connect(self._refresh_summary)
        self.coordinator.duplicate_found.connect(self._show_conflict_dialog)
        self.coordinator.mode_changed.connect(self._set_connection_mode)
        self.coordinator.notification.connect(self._show_notification)
        self.coordinator.item_terminal.connect(self._record_history)
        QTimer.singleShot(0, self._set_initial_connection_mode)

    def _install_shortcuts(self) -> None:
        choose_shortcut = QShortcut(QKeySequence("Ctrl+U"), self)
        choose_shortcut.activated.connect(self._choose_files)
        upload_shortcut = QShortcut(QKeySequence("Ctrl+1"), self)
        upload_shortcut.activated.connect(lambda: self._show_page(0))
        history_shortcut = QShortcut(QKeySequence("Ctrl+2"), self)
        history_shortcut.activated.connect(lambda: self._show_page(1))
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self._focus_history_search)
        self._shortcuts = [
            choose_shortcut,
            upload_shortcut,
            history_shortcut,
            search_shortcut,
        ]

    def _set_initial_connection_mode(self) -> None:
        self._set_connection_mode(self.coordinator.config.mode_label)

    def _set_connection_mode(self, message: str) -> None:
        self._connection_mode_message = message
        if hasattr(self, "connection_badge"):
            self.connection_badge.set_mode(message)

    def _change_conflict_policy(self, _index: int = -1) -> None:
        policy = self.conflict_select.currentData()
        if isinstance(policy, str):
            self.coordinator.set_conflict_policy(policy)
            self._show_notification(
                f"Tệp đang chờ sẽ dùng lựa chọn trùng tên: {self.conflict_select.currentText()}."
            )

    def _show_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self.nav_upload.setChecked(index == 0)
        self.nav_history.setChecked(index == 1)
        if index == 1:
            self._refresh_history()

    def _focus_history_search(self) -> None:
        self._show_page(1)
        self.history_search.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _choose_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Chọn tệp để tải lên",
            "",
            "Tệp hỗ trợ (*.txt *.pdf *.jpg *.jpeg *.doc *.docx)",
        )
        if paths:
            self.coordinator.add_files(paths)

    def _add_row(self, item_id: str) -> None:
        item = self.coordinator.get_item(item_id)
        if item is None:
            return
        row = FileRow(item)
        row.remove_requested.connect(self.coordinator.remove_item)
        row.action_requested.connect(self._handle_row_action)
        self.rows[item_id] = row
        self.list_layout.insertWidget(self.list_layout.count() - 1, row)

    def _update_row(self, item_id: str) -> None:
        item = self.coordinator.get_item(item_id)
        row = self.rows.get(item_id)
        if item is not None and row is not None:
            row.update_item(item)

    def _remove_row(self, item_id: str) -> None:
        row = self.rows.pop(item_id, None)
        if row is not None:
            row.deleteLater()

    def _handle_row_action(self, item_id: str) -> None:
        item = self.coordinator.get_item(item_id)
        if item is None:
            return
        if item.conflict_pending:
            self.coordinator.request_conflict_resolution(item_id)
        elif item.status is UploadStatus.ERROR:
            self.coordinator.retry(item_id)

    def _refresh_elapsed_times(self) -> None:
        for item_id, row in self.rows.items():
            item = self.coordinator.get_item(item_id)
            if item is not None:
                row.update_time(item)

    def _refresh_summary(self) -> None:
        stats = self.coordinator.queue.stats()
        for key, metric in self.stat_metrics.items():
            metric.set_value(stats[key])
        total = stats["Tổng"]
        self.list_meta.setText(
            f"{total} tệp · {stats[UploadStatus.UPLOADING.value]} đang tải · "
            f"{stats[UploadStatus.WAITING.value]} đang chờ"
            if total
            else "Chưa có tệp nào"
        )
        self.footer_summary.setText(
            f"Tổng {total} · Thành công {stats[UploadStatus.COMPLETED.value]} · "
            f"Lỗi {stats[UploadStatus.ERROR.value]} · "
            f"Đang chờ {stats[UploadStatus.WAITING.value]}"
        )
        self.empty_state.setVisible(total == 0)
        self.scroll.setVisible(total > 0)
        self.clear_button.setEnabled(total > 0)

    def _confirm_clear(self) -> None:
        active_count = self.coordinator.queue.stats()[UploadStatus.UPLOADING.value]
        message = "Bạn có chắc muốn xóa các tệp có thể xóa khỏi danh sách?"
        if active_count:
            message += "\nTệp đang tải sẽ được giữ lại đến khi hoàn tất."
        answer = QMessageBox.question(
            self,
            "Xóa danh sách tải lên",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            removed = self.coordinator.clear_removable()
            self._show_notification(f"Đã xóa {removed} tệp khỏi danh sách.")

    def _show_conflict_dialog(self, item_id: str) -> None:
        item = self.coordinator.get_item(item_id)
        if item is None:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Xử lý tệp trùng tên")
        dialog.setModal(True)
        dialog.setMinimumWidth(470)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(12)
        title = QLabel("Tệp đã tồn tại trên máy chủ")
        title.setObjectName("pageTitle")
        detail = QLabel(
            f'“{item.name}” trùng tên với một tệp trên server.\n'
            "Hãy chọn cách xử lý cho riêng tệp này."
        )
        detail.setObjectName("pageSubtitle")
        detail.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(detail)
        buttons = QHBoxLayout()
        buttons.addStretch()
        skip = QPushButton("Bỏ qua")
        rename = QPushButton("Đổi tên")
        overwrite = QPushButton("Ghi đè")
        overwrite.setObjectName("primaryButton")
        buttons.addWidget(skip)
        buttons.addWidget(rename)
        buttons.addWidget(overwrite)
        layout.addLayout(buttons)
        choice: dict[str, str] = {}

        def resolve(action: str) -> None:
            choice["action"] = action
            dialog.accept()

        skip.clicked.connect(lambda: resolve("skip"))
        rename.clicked.connect(lambda: resolve("rename"))
        overwrite.clicked.connect(lambda: resolve("overwrite"))
        dialog.exec()
        if action := choice.get("action"):
            self.coordinator.resolve_conflict(item_id, action)

    def _record_history(self, item: UploadItem, status: str) -> None:
        try:
            self.history_store.upsert(item, status)
        except OSError as error:
            self._show_notification(f"Không thể lưu lịch sử cục bộ: {error}")
            return
        self._refresh_history()

    def _refresh_history(self, *_args) -> None:  # noqa: ANN002
        if not hasattr(self, "history_layout"):
            return
        while self.history_layout.count() > 1:
            entry = self.history_layout.takeAt(0)
            widget = entry.widget()
            if widget is not None:
                widget.deleteLater()

        query = self.history_search.text().strip().casefold()
        selected_status = self.history_filter.currentText()
        records = self.history_store.list_records()
        filtered: list[HistoryRecord] = []
        for record in records:
            if query and query not in record.name.casefold():
                continue
            if selected_status != "Tất cả trạng thái" and record.status != selected_status:
                continue
            filtered.append(record)
        for record in filtered:
            self.history_layout.insertWidget(self.history_layout.count() - 1, HistoryRow(record))

        total = len(records)
        visible = len(filtered)
        self.history_meta.setText(
            f"{visible} / {total} bản ghi" if visible != total else f"{total} bản ghi"
        )
        self.history_empty.setVisible(visible == 0)
        self.history_scroll.setVisible(visible > 0)

    def _show_notification(self, message: str) -> None:
        self.statusBar().showMessage(message, 4500)
