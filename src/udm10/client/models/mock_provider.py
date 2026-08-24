"""Responsive mock provider used until the TCP upload adapter is implemented."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QObject, QTimer, Signal

from udm10.client.models.history import HistoryEntry, HistoryResult
from udm10.client.models.upload import ConflictPolicy, UploadItem, UploadStatus


class MockUiDataProvider(QObject):
    uploads_changed = Signal(object)
    history_changed = Signal(object)
    history_loading_changed = Signal(bool)
    history_error = Signal(str)
    connection_changed = Signal(bool)
    duplicate_detected = Signal(str)

    def __init__(self, *, auto_advance: bool = True, parent=None) -> None:
        super().__init__(parent)
        self._uploads: list[UploadItem] = []
        self._history: list[HistoryEntry] = []
        self._online = True
        self._timer = QTimer(self)
        self._timer.setInterval(450)
        self._timer.timeout.connect(self._advance_uploads)
        self.load_mixed_scenario()
        if auto_advance:
            self._timer.start()

    def current_uploads(self) -> tuple[UploadItem, ...]:
        return tuple(self._uploads)

    def current_history(self) -> tuple[HistoryEntry, ...]:
        return tuple(self._history)

    def add_files(self, paths: list[Path]) -> None:
        existing_names = {item.name.casefold() for item in self._uploads}
        conflicts: list[str] = []
        for path in paths:
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            duplicate = path.name.casefold() in existing_names
            item = UploadItem(
                    id=uuid4().hex,
                    name=path.name,
                    size_bytes=size,
                    status=UploadStatus.WAITING,
                    duplicate_conflict=duplicate,
                    source_path=path,
                )
            self._uploads.append(item)
            if duplicate:
                conflicts.append(item.id)
            existing_names.add(path.name.casefold())
        self._normalize_queue_positions()
        self._emit_uploads()
        for upload_id in conflicts:
            self.duplicate_detected.emit(upload_id)

    def retry_upload(self, upload_id: str) -> None:
        self._replace_upload(
            upload_id,
            status=UploadStatus.WAITING,
            progress=0,
            bytes_sent=0,
            speed_bytes_per_second=0.0,
            error_message=None,
        )
        self._normalize_queue_positions()
        self._emit_uploads()

    def remove_upload(self, upload_id: str) -> None:
        self._uploads = [item for item in self._uploads if item.id != upload_id]
        self._normalize_queue_positions()
        self._emit_uploads()

    def resolve_duplicate(
        self, upload_id: str, policy: ConflictPolicy, apply_to_remaining: bool
    ) -> None:
        targets = [upload_id]
        if apply_to_remaining:
            targets.extend(
                item.id
                for item in self._uploads
                if item.duplicate_conflict and item.id != upload_id
            )
        if policy == ConflictPolicy.SKIP:
            skipped = [item for item in self._uploads if item.id in targets]
            for item in skipped:
                self._replace_upload(
                    item.id,
                    status=UploadStatus.SKIPPED,
                    duplicate_conflict=False,
                    queue_position=None,
                )
                self._history.insert(
                    0,
                    HistoryEntry(
                        id=uuid4().hex,
                        name=item.name,
                        completed_at=datetime.now(),
                        size_bytes=item.size_bytes,
                        result=HistoryResult.SKIPPED,
                    ),
                )
            self.history_changed.emit(self.current_history())
        else:
            for target in targets:
                self._replace_upload(target, duplicate_conflict=False)
        self._normalize_queue_positions()
        self._emit_uploads()

    def refresh_history(self) -> None:
        self.history_loading_changed.emit(True)
        QTimer.singleShot(500, self._finish_history_refresh)

    def retry_connection(self) -> None:
        QTimer.singleShot(650, lambda: self.set_online(True))

    def set_online(self, online: bool) -> None:
        self._online = online
        if not online:
            # An interrupted transfer cannot remain semantically "uploading".
            # Preserve its progress so a future real adapter can offer retry,
            # while each other queued/completed file keeps its own state.
            self._uploads = [
                item.updated(
                    status=UploadStatus.FAILED,
                    speed_bytes_per_second=0.0,
                    error_message="Mất kết nối máy chủ. Hãy kết nối lại rồi thử lại.",
                )
                if item.status == UploadStatus.UPLOADING
                else item
                for item in self._uploads
            ]
            self._normalize_queue_positions()
            self._emit_uploads()
        self.connection_changed.emit(online)

    def set_uploads(self, uploads: list[UploadItem]) -> None:
        self._uploads = list(uploads)
        self._normalize_queue_positions()
        self._emit_uploads()

    def set_history(self, history: list[HistoryEntry], *, loading: bool = False) -> None:
        self._history = list(history)
        self.history_loading_changed.emit(loading)
        if not loading:
            self.history_changed.emit(self.current_history())

    def load_empty_scenario(self) -> None:
        self.set_uploads([])

    def load_mixed_scenario(self) -> None:
        self._uploads = _mixed_uploads()
        self._history = _sample_history()
        self._normalize_queue_positions()

    def _finish_history_refresh(self) -> None:
        self.history_loading_changed.emit(False)
        self.history_changed.emit(self.current_history())

    def _advance_uploads(self) -> None:
        if not self._online:
            return
        active_count = sum(
            item.status == UploadStatus.UPLOADING for item in self._uploads
        )
        available_slots = max(0, 2 - active_count)
        if available_slots:
            for index, item in enumerate(self._uploads):
                if available_slots == 0:
                    break
                if item.status == UploadStatus.WAITING and item.duplicate_conflict:
                    break
                if item.status == UploadStatus.WAITING:
                    self._uploads[index] = item.updated(
                        status=UploadStatus.UPLOADING,
                        queue_position=None,
                        speed_bytes_per_second=2_400_000.0,
                    )
                    available_slots -= 1

        changed = False
        for index, item in enumerate(tuple(self._uploads)):
            if item.status != UploadStatus.UPLOADING:
                continue
            changed = True
            next_progress = min(100, item.progress + 3)
            if next_progress >= 100:
                completed = item.updated(
                    status=UploadStatus.COMPLETED,
                    progress=100,
                    speed_bytes_per_second=0.0,
                )
                self._uploads[index] = completed
                self._history.insert(
                    0,
                    HistoryEntry(
                        id=uuid4().hex,
                        name=completed.name,
                        completed_at=datetime.now(),
                        size_bytes=completed.size_bytes,
                        result=HistoryResult.SUCCESS,
                    ),
                )
                self.history_changed.emit(self.current_history())
            else:
                speed = 1_700_000.0 + (index % 4) * 620_000.0
                self._uploads[index] = item.updated(
                    progress=next_progress,
                    speed_bytes_per_second=speed,
                )
        if changed:
            self._normalize_queue_positions()
            self._emit_uploads()

    def _replace_upload(self, upload_id: str, **changes: object) -> None:
        for index, item in enumerate(self._uploads):
            if item.id == upload_id:
                self._uploads[index] = item.updated(**changes)
                return

    def _normalize_queue_positions(self) -> None:
        position = 1
        normalized: list[UploadItem] = []
        for item in self._uploads:
            if item.status == UploadStatus.WAITING:
                normalized.append(item.updated(queue_position=position))
                position += 1
            else:
                normalized.append(item.updated(queue_position=None))
        self._uploads = normalized

    def _emit_uploads(self) -> None:
        self.uploads_changed.emit(self.current_uploads())


def _mixed_uploads() -> list[UploadItem]:
    return [
        UploadItem("u1", "Báo cáo tài chính quý III — bản đã ký.pdf", 13_002_342, UploadStatus.UPLOADING, 76, 4_200_000.0),
        UploadItem("u2", "ảnh_sự_kiện_Đà_Nẵng_2026.jpg", 7_142_941, UploadStatus.UPLOADING, 48, 2_100_000.0),
        UploadItem("u3", "Hợp đồng lao động.docx", 1_363_149, UploadStatus.WAITING),
        UploadItem(
            "u4",
            "Tài liệu đào tạo nội bộ phiên bản rất dài để kiểm tra cách hiển thị tên tệp trong danh sách.zip",
            88_185_241,
            UploadStatus.FAILED,
            error_message="Không thể kết nối tới máy chủ. Kiểm tra kết nối rồi thử lại.",
        ),
        UploadItem("u5", "readme_unicode_测试_пример.txt", 82_102, UploadStatus.COMPLETED, 100),
        UploadItem("u6", "Báo cáo.pdf", 2_936_012, UploadStatus.WAITING, duplicate_conflict=True),
        UploadItem("u7", "video_demo.mp4", 43_275_901, UploadStatus.WAITING),
        UploadItem("u8", "dữ_liệu_khách_hàng.csv", 5_278_190, UploadStatus.COMPLETED, 100),
        UploadItem(
            "u9",
            "presentation-final.pptx",
            9_812_244,
            UploadStatus.FAILED,
            error_message="Máy chủ không thể lưu tệp. Thử lại sau.",
        ),
        UploadItem("u10", "logo-udm.png", 364_128, UploadStatus.COMPLETED, 100),
    ]


def _sample_history() -> list[HistoryEntry]:
    now = datetime.now().replace(second=0, microsecond=0)
    return [
        HistoryEntry("h1", "Báo cáo tháng 08.pdf", now - timedelta(minutes=4), 13_002_342, HistoryResult.SUCCESS),
        HistoryEntry("h2", "Hợp đồng lao động_1.docx", now - timedelta(minutes=9), 1_363_149, HistoryResult.RENAMED),
        HistoryEntry("h3", "readme_unicode_测试_пример.txt", now - timedelta(minutes=13), 82_102, HistoryResult.SUCCESS),
        HistoryEntry("h4", "tai-lieu.zip", now - timedelta(minutes=22), 88_185_241, HistoryResult.FAILED),
        HistoryEntry("h5", "ảnh_sự_kiện_Đà_Nẵng_2026.jpg", now - timedelta(days=1), 7_142_941, HistoryResult.SUCCESS),
        HistoryEntry("h6", "Báo cáo.pdf", now - timedelta(days=1, minutes=8), 2_936_012, HistoryResult.SKIPPED),
    ]
