"""Render current desktop states offscreen for visual verification evidence."""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog


CODE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = CODE_ROOT.parent
CLIENT_ROOT = CODE_ROOT / "ui-handoff" / "client"
sys.path.insert(0, str(CLIENT_ROOT))

from multiple_upload_client.config import ClientConfig
from multiple_upload_client.history import HistoryStore
from multiple_upload_client.main_window import MainWindow
from multiple_upload_client.models import UploadStatus


def config() -> ClientConfig:
    return ClientConfig(
        transport="tcp",
        tcp_host="127.0.0.1",
        tcp_port=9000,
        base_url="",
        upload_endpoint="/api/uploads",
        allow_mock_fallback=False,
        max_concurrent=3,
        max_upload_size=512_000,
        conflict_policy="ask",
    )


def main() -> int:
    evidence = PROJECT_ROOT / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    application = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        names = [
            "báo-cáo-quý-III.txt",
            "ảnh-sản-phẩm-độ-phân-giải-cao.jpg",
            "tài-liệu-đang-chờ.pdf",
            "tên-tệp-rất-dài-cần-được-rút-gọn-mà-không-làm-vỡ-bố-cục.docx",
            "bỏ-qua-trùng-tên.txt",
            "xung-đột-cần-xử-lý.txt",
        ]
        paths = []
        for index, name in enumerate(names):
            path = root / name
            path.write_bytes((f"sample-{index}" * 20).encode("utf-8"))
            paths.append(path)

        window = MainWindow(config(), HistoryStore(root / "history.json"))
        items = window.coordinator.queue.add_paths(paths)
        states = [
            UploadStatus.UPLOADING,
            UploadStatus.COMPLETED,
            UploadStatus.WAITING,
            UploadStatus.ERROR,
            UploadStatus.SKIPPED,
            UploadStatus.WAITING,
        ]
        for item, state in zip(items, states):
            item.status = state
            if state is UploadStatus.UPLOADING:
                item.progress = 47
                item.speed = "1,8 MB/s"
                item.detail = "Đang gửi dữ liệu"
            elif state is UploadStatus.COMPLETED:
                item.progress = 100
                item.detail = "Server đã lưu an toàn"
                item.finished_at = datetime.now().astimezone()
            elif state is UploadStatus.ERROR:
                item.progress = 31
                item.detail = "Mất kết nối khi đang gửi. Hãy thử lại."
                item.finished_at = datetime.now().astimezone()
            elif state is UploadStatus.SKIPPED:
                item.detail = "Đã bỏ qua vì tên tệp đã tồn tại"
                item.conflict_result = "Bỏ qua"
                item.finished_at = datetime.now().astimezone()
            window._add_row(item.id)
        items[-1].conflict_pending = True
        items[-1].detail = "Tên tệp đã tồn tại trên Server — cần chọn cách xử lý"
        window._update_row(items[-1].id)
        ready_state = {
            "state": "ready",
            "message": "Server UDM sẵn sàng nhận tệp",
            "host": "127.0.0.1",
            "port": 9000,
            "active_uploads": 0,
            "upload_limit": 3,
            "checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "busy": False,
        }
        window._refresh_summary()
        outputs = []
        for width, height in ((1366, 768), (1120, 700), (1920, 1080)):
            window.resize(width, height)
            window.show()
            application.processEvents()
            window._set_connection_state(ready_state)
            application.processEvents()
            target = evidence / f"gui-{width}x{height}.png"
            window.grab().save(str(target))
            outputs.append(str(target.relative_to(PROJECT_ROOT)))

        dialog_path = evidence / "gui-duplicate-dialog.png"

        def capture_dialog() -> None:
            for widget in application.topLevelWidgets():
                if isinstance(widget, QDialog) and widget.isVisible():
                    widget.grab().save(str(dialog_path))
                    widget.reject()
                    return

        QTimer.singleShot(100, capture_dialog)
        window._show_conflict_dialog(items[-1].id)
        application.processEvents()
        if dialog_path.exists():
            outputs.append(str(dialog_path.relative_to(PROJECT_ROOT)))
        window.close()

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "platform": f"PySide6 {os.getenv('QT_QPA_PLATFORM', 'default')}",
        "states": [
            "waiting",
            "uploading",
            "completed",
            "failed",
            "skipped",
            "duplicate conflict",
            "UDM server ready",
        ],
        "screenshots": outputs,
    }
    (evidence / "ui-evidence.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
