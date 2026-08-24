# Manifest gói UI client UDM_10

Gói gồm **15 file**: 12 file được sao chép nguyên trạng từ client hiện có và 3
file mới dành riêng cho bàn giao (`README.md`, `MANIFEST.md`,
`config.example.json`).

| Đường dẫn gốc | Đường dẫn trong gói | Lý do giữ | Phụ thuộc/import liên quan |
|---|---|---|---|
| `client/run.py` | `ui-handoff/client/run.py` | Entry point chạy client độc lập. | Import `multiple_upload_client.__main__.main`. |
| `client/requirements.txt` | `ui-handoff/client/requirements.txt` | Khai báo dependency UI tái lập được. | `PySide6==6.9.1`. |
| `client/multiple_upload_client/__init__.py` | `ui-handoff/client/multiple_upload_client/__init__.py` | Khai báo Python package. | Được Python import trước các module con. |
| `client/multiple_upload_client/__main__.py` | `ui-handoff/client/multiple_upload_client/__main__.py` | Khởi tạo QApplication và MainWindow. | Import `config.ClientConfig`, `main_window.MainWindow`, PySide6. |
| `client/multiple_upload_client/main_window.py` | `ui-handoff/client/multiple_upload_client/main_window.py` | Layout chính, điều hướng upload/lịch sử, dialog tên trùng. | Import `config`, `history`, `models`, `theme`, `uploader`, `widgets`, PySide6. |
| `client/multiple_upload_client/widgets.py` | `ui-handoff/client/multiple_upload_client/widgets.py` | Component, logo/icon vector, drop zone, hàng file và lịch sử. | Import `history.HistoryRecord`, `models.UploadItem/UploadStatus`, PySide6. |
| `client/multiple_upload_client/theme.py` | `ui-handoff/client/multiple_upload_client/theme.py` | Màu, typography, spacing và Qt stylesheet dùng chung. | Được `main_window.py` và `__main__.py` sử dụng. |
| `client/multiple_upload_client/models.py` | `ui-handoff/client/multiple_upload_client/models.py` | Dữ liệu hiển thị cho file/status/progress. **Cần nhóm xác nhận** nếu đích có model riêng. | Được `widgets.py`, `queue_manager.py`, `history.py`, `uploader.py` import. |
| `client/multiple_upload_client/queue_manager.py` | `ui-handoff/client/multiple_upload_client/queue_manager.py` | Hàng đợi và giới hạn 6 upload đồng thời. **Cần nhóm xác nhận** khi merge logic. | Import `models.UploadItem/UploadStatus`; được `uploader.py` import. |
| `client/multiple_upload_client/uploader.py` | `ui-handoff/client/multiple_upload_client/uploader.py` | Coordinator/signals mà UI gọi trực tiếp; giữ để gói chạy độc lập. **Cần nhóm xác nhận** API adapter. | Import `config`, `models`, `queue_manager`, QtNetwork. |
| `client/multiple_upload_client/history.py` | `ui-handoff/client/multiple_upload_client/history.py` | Cung cấp model/store cho trang lịch sử. **Cần nhóm xác nhận** khi backend có API lịch sử. | Import `models.UploadItem`; được `main_window.py`, `widgets.py` import. |
| `client/multiple_upload_client/config.py` | `ui-handoff/client/multiple_upload_client/config.py` | Config URL/endpoint không hard-code; cần cho bootstrap/uploader. **Cần nhóm xác nhận** config chung của nhánh đích. | Được `__main__.py`, `main_window.py`, `uploader.py` import. |
| — (tạo cho gói) | `ui-handoff/client/config.example.json` | Cấu hình mẫu sạch; thay thế config máy cá nhân bị loại. | Được `ClientConfig.load()` đọc sau khi người dùng chủ động sao chép thành `config.json`. |
| — (tạo cho gói) | `ui-handoff/README.md` | Hướng dẫn phạm vi, tích hợp, tương thích và kiểm tra. | Không tham gia runtime. |
| — (tạo cho gói) | `ui-handoff/MANIFEST.md` | Truy vết từng file bàn giao và dependency nội bộ. | Không tham gia runtime. |

## Tóm tắt loại trừ

19 file project-visible không được sao chép: toàn bộ source/test/dependency của
server; test và script render client; config máy cá nhân; README/tài liệu thiết
kế nguồn. Các thư mục/file sinh tự động như `.venv`, cache, log, build,
`__pycache__`, `.git`, `.env` và lịch sử thật cũng không được đưa vào gói và
không tính trong con số 19.
