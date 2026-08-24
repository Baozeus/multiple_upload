# UDM_10 — Multiple Upload

Ứng dụng Python 3.11+ desktop client-server upload nhiều file. UI PySide6 dùng
TCP adapter thật; queue FIFO thread-safe giới hạn `N` worker nền, cập nhật
progress/tốc độ từng file về GUI bằng Qt signal. TCP server nhận binary theo
chunk, lưu nguyên tử, hỗ trợ Unicode và trả kết quả riêng từng file.

## Kiến trúc đã chốt

- Desktop GUI: PySide6.
- Transport chính: TCP.
- Control message: JSON UTF-8 với length-prefix 4 byte, big-endian.
- File payload: raw binary đúng số byte đã khai báo, chỉ gửi sau `upload.ready`.
- Trùng tên: server trả `upload.conflict`; client luôn chờ người dùng chọn
  `overwrite`, `rename` hoặc `skip`, không có policy mặc định.
- Storage: stream theo chunk vào file `.part`, sau đó commit atomic.
- Client queue: `MAX_CONCURRENT_UPLOADS`, mặc định cấu hình mẫu là 3.
- Trạng thái: `waiting`, `uploading`, `completed`, `failed`, `skipped`.
- History: MySQL 8.0+ khi `MYSQL_ENABLED=true`; JSON khi tắt.
- History được sở hữu bởi server và đọc qua TCP trong worker riêng; khởi động
  client tự tải lại dữ liệu bền vững mà không chặn GUI.
- Source layout: `src/udm10`.

`domain` và `protocol` không phụ thuộc PySide6 hoặc MySQL. Entry point chỉ gọi
module bootstrap và không chứa business logic.

## Thiết lập

```powershell
cd D:\UDM
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Không commit `.env`, mật khẩu MySQL, file upload, history runtime hoặc log.

## Chạy

```powershell
python run_server.py
python run_client.py
```

Server xử lý `health.check` và nhiều `upload.start` nối tiếp trên một connection.
Chi tiết message, error code và conflict policy xem tại
[`docs/tcp-protocol.md`](docs/tcp-protocol.md). Mỗi worker client dùng một TCP
connection riêng để cô lập lỗi; số worker đồng thời luôn bị queue giới hạn bởi N.

Thiết lập schema và tài khoản MySQL xem tại
[`docs/mysql-setup.md`](docs/mysql-setup.md). Khi MySQL được bật nhưng không thể
kết nối hoặc thiếu schema, server dừng trước khi bind cổng và trả mã lỗi `2`.

## Kiểm tra

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest tests\unit -q
python -m pytest tests\integration -q
python -m pytest tests\ui -q
python -m compileall -q src run_client.py run_server.py
```

Regression cuối: **65 test + 12 subtests đạt**. TC-01..TC-32 đạt; TC-33
Pause/Resume là N/A theo phạm vi. Xem
[`docs/test-report.md`](docs/test-report.md).

## Tài liệu bàn giao

- [Kiến trúc](docs/architecture.md)
- [TCP protocol](docs/tcp-protocol.md)
- [Thiết lập MySQL](docs/mysql-setup.md)
- [Hướng dẫn người dùng](docs/user-guide.md)
- [Kết quả kiểm thử](docs/test-report.md)
- [Phân công và đóng góp](docs/team-contribution.md)

## Cấu hình còn chờ xác nhận

- `MAX_FILE_SIZE_MB`
- `ALLOWED_EXTENSIONS`
- Tên/vai trò TV1–TV6 giữa PDF và DOCX.

Không push `.env`, upload thật, JSON history, log, cache, virtual environment,
dump database, `.qa` hoặc `.impeccable`.
