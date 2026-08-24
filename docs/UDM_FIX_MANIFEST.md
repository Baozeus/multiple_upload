# UDM Fix — danh sách file tích hợp

Thư mục này chỉ chứa các file đã thêm hoặc chỉnh sửa để tích hợp giao diện PySide6 với TCP Server hiện hữu. Cấu trúc đường dẫn được giữ nguyên để có thể đối chiếu hoặc sao chép vào project.

## File Server và protocol

- `Code/protocol.py`
- `Code/server.py`
- `Code/upload_handler.py`
- `Code/duplicate_handler.py`
- `Code/codelogic.py`
- `Code/README.md`

## File Client giao diện mới

- `ui-handoff/client/config.example.json`
- `ui-handoff/client/README.md`
- `ui-handoff/client/multiple_upload_client/config.py`
- `ui-handoff/client/multiple_upload_client/main_window.py`
- `ui-handoff/client/multiple_upload_client/queue_manager.py`
- `ui-handoff/client/multiple_upload_client/tcp_transport.py`
- `ui-handoff/client/multiple_upload_client/uploader.py`
- `ui-handoff/client/multiple_upload_client/widgets.py`

## Test và tài liệu

- `tests/test_config_and_queue.py`
- `tests/test_legacy_queue.py`
- `tests/test_protocol_and_storage.py`
- `tests/test_tcp_smoke.py`
- `docs/UI_INTEGRATION_REPORT.md`
- `docs/UDM_FIX_MANIFEST.md`
- `README.md`

## Kết quả xác minh

- 17/17 test pass.
- TCP là transport mặc định.
- HTTP Adapter được giữ để tương thích cấu hình cũ.
- Client TCP cũ không gửi `conflict` vẫn mặc định `rename`.
- Không chứa `.git`, `.env`, cache, log, file build hoặc dữ liệu upload.

## Chạy test

```powershell
python -B -m unittest discover -s tests -v
```

## Chạy ứng dụng

```powershell
python Code\server.py --host 127.0.0.1 --port 9000
python ui-handoff\client\run.py
```

Giao diện mới yêu cầu dependency đã khai báo trong `ui-handoff/client/requirements.txt`: `PySide6==6.9.1`.
