"""Asynchronous upload coordinator backed by Qt Network."""

from __future__ import annotations

from functools import partial
from datetime import datetime
import time

from PySide6.QtCore import QFile, QIODevice, QObject, QTimer, QUrl, QUrlQuery, Signal
from PySide6.QtNetwork import (
    QHttpMultiPart,
    QHttpPart,
    QNetworkAccessManager,
    QNetworkReply,
    QNetworkRequest,
)

from .config import ClientConfig
from .models import UploadItem, UploadStatus
from .queue_manager import UploadQueue


class UploadCoordinator(QObject):
    item_added = Signal(str)
    item_updated = Signal(str)
    item_removed = Signal(str)
    duplicate_found = Signal(str)
    queue_changed = Signal()
    mode_changed = Signal(str)
    notification = Signal(str)
    item_terminal = Signal(object, str)

    def __init__(self, config: ClientConfig, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.queue = UploadQueue()
        self.network = QNetworkAccessManager(self)
        self._network_replies: dict[str, QNetworkReply] = {}
        self._mock_timers: dict[str, QTimer] = {}
        self._progress_samples: dict[str, tuple[float, int]] = {}

        if config.upload_url:
            self.mode_changed.emit(f"API: {config.base_url}")
        else:
            self.mode_changed.emit("Chế độ mô phỏng")

    def add_files(self, paths: list[str]) -> None:
        added = self.queue.add_paths(paths)
        for item in added:
            self.item_added.emit(item.id)
        if added:
            self.notification.emit(f"Đã thêm {len(added)} tệp vào danh sách.")
        elif paths:
            self.notification.emit("Không có tệp hợp lệ mới được thêm.")
        self.queue_changed.emit()
        self._pump_queue()

    def get_item(self, item_id: str) -> UploadItem | None:
        return self.queue.items.get(item_id)

    def remove_item(self, item_id: str) -> None:
        if self.queue.remove(item_id):
            self.item_removed.emit(item_id)
            self.queue_changed.emit()
            self._pump_queue()

    def clear_removable(self) -> int:
        previous_ids = set(self.queue.items)
        removed_count = self.queue.clear_removable()
        for item_id in previous_ids - set(self.queue.items):
            self.item_removed.emit(item_id)
        self.queue_changed.emit()
        return removed_count

    def retry(self, item_id: str) -> None:
        item = self.get_item(item_id)
        if item is None or item.status is UploadStatus.UPLOADING:
            return
        item.reset_for_retry()
        self.item_updated.emit(item.id)
        self.queue_changed.emit()
        self._pump_queue()

    def request_conflict_resolution(self, item_id: str) -> None:
        item = self.get_item(item_id)
        if item is not None and item.conflict_pending:
            self.duplicate_found.emit(item_id)

    def resolve_conflict(self, item_id: str, action: str) -> None:
        item = self.get_item(item_id)
        if item is None or not item.conflict_pending:
            return
        if action == "skip":
            item.conflict_result = "Bỏ qua"
            item.finished_at = datetime.now().astimezone()
            self.item_terminal.emit(item, "Bỏ qua")
            self.queue.remove(item_id)
            self.item_removed.emit(item_id)
            self.notification.emit(f"Đã bỏ qua tệp trùng tên “{item.name}”.")
        elif action in {"overwrite", "rename"}:
            item.reset_for_retry()
            item.conflict_policy = action
            item.conflict_result = "Ghi đè" if action == "overwrite" else "Đổi tên"
            self.item_updated.emit(item_id)
        self.queue_changed.emit()
        self._pump_queue()

    def _pump_queue(self) -> None:
        for item in self.queue.take_next():
            self.item_updated.emit(item.id)
            if self.config.upload_url:
                self._start_network_upload(item)
            else:
                self._start_mock_upload(item)
        self.queue_changed.emit()

    def _start_network_upload(self, item: UploadItem) -> None:
        source = QFile(str(item.path))
        if not source.open(QIODevice.OpenModeFlag.ReadOnly):
            self._mark_error(item, "Không thể đọc tệp hoặc không có quyền truy cập.")
            return

        url = QUrl(self.config.upload_url)
        if item.conflict_policy:
            query = QUrlQuery(url)
            query.addQueryItem("conflict", item.conflict_policy)
            url.setQuery(query)

        request = QNetworkRequest(url)
        request.setRawHeader(b"Accept", b"application/json")

        multipart = QHttpMultiPart(QHttpMultiPart.ContentType.FormDataType)
        file_part = QHttpPart()
        safe_name = item.name.replace('"', "")
        file_part.setRawHeader(
            b"Content-Disposition",
            f'form-data; name="file"; filename="{safe_name}"'.encode("utf-8"),
        )
        file_part.setBodyDevice(source)
        source.setParent(multipart)
        multipart.append(file_part)

        reply = self.network.post(request, multipart)
        multipart.setParent(reply)
        self._network_replies[item.id] = reply
        self._progress_samples[item.id] = (time.monotonic(), 0)
        reply.uploadProgress.connect(partial(self._on_upload_progress, item.id))
        reply.finished.connect(partial(self._on_network_finished, item.id, reply))
        item.detail = "Đang gửi đến máy chủ"
        self.item_updated.emit(item.id)

    def _on_upload_progress(self, item_id: str, sent: int, total: int) -> None:
        item = self.get_item(item_id)
        if item is None or item.status is not UploadStatus.UPLOADING:
            return
        if total > 0:
            item.progress = max(0, min(99, int(sent * 100 / total)))

        now = time.monotonic()
        previous_time, previous_bytes = self._progress_samples.get(item_id, (now, sent))
        elapsed = now - previous_time
        if elapsed >= 0.25:
            item.speed = self._format_speed((sent - previous_bytes) / elapsed)
            self._progress_samples[item_id] = (now, sent)
        self.item_updated.emit(item_id)

    def _on_network_finished(self, item_id: str, reply: QNetworkReply) -> None:
        item = self.get_item(item_id)
        self._network_replies.pop(item_id, None)
        self._progress_samples.pop(item_id, None)
        status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        error_text = reply.errorString()
        network_error = reply.error()
        reply.deleteLater()

        if item is None:
            self._pump_queue()
            return
        if status is not None and 200 <= int(status) < 300:
            item.status = UploadStatus.COMPLETED
            item.progress = 100
            item.speed = "—"
            item.detail = "Đã tải lên an toàn"
            item.finished_at = datetime.now().astimezone()
            self.item_updated.emit(item.id)
            self.item_terminal.emit(item, UploadStatus.COMPLETED.value)
            self.mode_changed.emit(f"API đang hoạt động — {self.config.base_url}")
            item.conflict_policy = None
        elif status is not None and int(status) == 409:
            item.status = UploadStatus.WAITING
            item.progress = 0
            item.speed = "—"
            item.detail = "Tên tệp đã tồn tại trên máy chủ"
            item.conflict_pending = True
            self.item_updated.emit(item.id)
            self.duplicate_found.emit(item.id)
        elif self._should_use_mock_fallback(status, network_error, item):
            item.used_mock_fallback = True
            item.status = UploadStatus.UPLOADING
            item.progress = 0
            item.detail = "API chưa sẵn sàng — đang mô phỏng upload"
            self.mode_changed.emit("Mock fallback — API upload chưa sẵn sàng")
            self.item_updated.emit(item.id)
            self._start_mock_upload(item)
            return
        else:
            self._mark_error(item, error_text or "Máy chủ từ chối tệp.")
            return
        self.queue_changed.emit()
        self._pump_queue()

    def _should_use_mock_fallback(
        self,
        status: object,
        network_error: QNetworkReply.NetworkError,
        item: UploadItem,
    ) -> bool:
        if not self.config.allow_mock_fallback or item.used_mock_fallback:
            return False
        unavailable_status = status is None or int(status) in {404, 405, 501}
        return unavailable_status or network_error in {
            QNetworkReply.NetworkError.ConnectionRefusedError,
            QNetworkReply.NetworkError.HostNotFoundError,
        }

    def _start_mock_upload(self, item: UploadItem) -> None:
        timer = QTimer(self)
        timer.setInterval(220)
        timer.timeout.connect(partial(self._advance_mock_upload, item.id))
        self._mock_timers[item.id] = timer
        item.status = UploadStatus.UPLOADING
        item.speed = "2,4 MB/s"
        if not item.used_mock_fallback:
            item.detail = "Đang mô phỏng upload"
            self.mode_changed.emit("Chế độ mô phỏng — chưa cấu hình API")
        item.used_mock_fallback = True
        timer.start()

    def _advance_mock_upload(self, item_id: str) -> None:
        item = self.get_item(item_id)
        timer = self._mock_timers.get(item_id)
        if item is None or timer is None:
            return
        item.progress = min(100, item.progress + 4)
        item.speed = f"{1.5 + (item.progress % 18) / 10:.1f} MB/s".replace(".", ",")
        if item.progress >= 100:
            timer.stop()
            timer.deleteLater()
            self._mock_timers.pop(item_id, None)
            item.status = UploadStatus.COMPLETED
            item.speed = "—"
            item.detail = "Đã hoàn tất trong chế độ mô phỏng"
            item.finished_at = datetime.now().astimezone()
        self.item_updated.emit(item.id)
        self.queue_changed.emit()
        if item.status is UploadStatus.COMPLETED:
            self.item_terminal.emit(item, UploadStatus.COMPLETED.value)
            self._pump_queue()

    def _mark_error(self, item: UploadItem, message: str) -> None:
        item.status = UploadStatus.ERROR
        item.speed = "—"
        item.detail = message
        item.finished_at = datetime.now().astimezone()
        self.item_updated.emit(item.id)
        self.item_terminal.emit(item, UploadStatus.ERROR.value)
        self.queue_changed.emit()
        self._pump_queue()

    @staticmethod
    def _format_speed(bytes_per_second: float) -> str:
        if bytes_per_second >= 1024 * 1024:
            return f"{bytes_per_second / (1024 * 1024):.1f} MB/s".replace(".", ",")
        if bytes_per_second >= 1024:
            return f"{bytes_per_second / 1024:.0f} KB/s"
        return f"{max(0, bytes_per_second):.0f} B/s"
