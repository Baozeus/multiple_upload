# Chạy và kiểm chứng UDM_FIXED

Giới hạn đã xác nhận: tối đa 6 tệp hợp lệ mỗi lần thêm, tối đa 3 upload hoạt động và tối đa 500 KiB (512.000 byte) mỗi tệp.

## Yêu cầu

- Windows 10/11, Python 3.10+.
- Client: `PySide6==6.9.1` (hoặc bản tương thích đã cài).
- MySQL chỉ cần khi chủ động kiểm tra module metadata; demo TCP không cần database.

## Cài dependency

```powershell
cd D:\UDM\UDM_FIXED
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r Code\ui-handoff\client\requirements.txt
```

## Chạy ứng dụng

Terminal 1:

```powershell
cd D:\UDM\UDM_FIXED
.\.venv\Scripts\python.exe Code\server.py --host 127.0.0.1 --port 9000 --dir uploads
```

Terminal 2:

```powershell
cd D:\UDM\UDM_FIXED
.\.venv\Scripts\python.exe Code\ui-handoff\client\run.py
```

Trong Client:

1. Kiểm tra `127.0.0.1` và `9000`.
2. Bấm **Kiểm tra kết nối**. Chỉ trạng thái **Server UDM sẵn sàng** mới xác nhận đúng giao thức.
3. Kéo-thả hoặc chọn tối đa 6 tệp. Tối đa 3 tệp chạy đồng thời.
4. Khi trùng tên, chọn riêng `Đổi tên`, `Ghi đè` hoặc `Bỏ qua` trên dialog.

## Chạy regression

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -B -m unittest discover -s Code\tests -v
```

Package MySQL (không kết nối DB thật):

```powershell
$env:PYTHONPATH=(Resolve-Path 'Code\mysql_database\src').Path
.\.venv\Scripts\python.exe -B -m pytest Code\mysql_database\tests -q
```

Tạo lại log kiểm chứng hiện hành:

```powershell
.\.venv\Scripts\python.exe -B Code\tests\run_verified_suite.py
```

## Chạy riêng 5 test mục tiêu

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -B -m unittest `
  Code.tests.test_config_and_queue.QueueTests.test_rejected_overflow_never_enters_queue_and_can_be_added_next_time `
  Code.tests.test_connection_coordinator.CoordinatorConnectionTests.test_eight_file_batch_reports_exact_six_accepted_two_rejected_message `
  Code.tests.test_tcp_smoke.TcpUploadSmokeTests.test_progress_is_monotonic_and_waits_for_server_ack_before_success `
  Code.tests.test_target_tcp_integration `
  Code.tests.test_ui_connection_controls.ConnectionControlsUiTests.test_endpoint_fields_are_locked_until_waiting_and_uploading_items_finish `
  -v
```

Các test TCP mục tiêu tự tạo thư mục tạm, server localhost và port trống; không ghi vào `uploads/` thật.

## Tái kiểm tra thủ công

### TC_3

Chọn đúng 6 tệp hợp lệ, mỗi tệp không quá 512.000 byte. Quan sát tối đa 3 dòng `Đang tải`, ba dòng còn lại `Chờ`, sau đó cả 6 `Hoàn tất`.

### TC_4

Chọn 8 tệp hợp lệ trong cùng một hộp chọn hoặc kéo-thả. Chỉ 6 tên đầu xuất hiện trong danh sách; dialog liệt kê 2 tên cuối và status bar hiển thị câu giới hạn batch. Chọn lại 2 tệp đó ở lần sau để xác nhận chúng vẫn được nhận.

### TC_9

Dùng test ACK trễ ở trên. Khi payload đã gửi xong, dòng tệp phải giữ `Đang tải`, 99% và “Đang chờ Server xác nhận”; chỉ chuyển 100%/`Hoàn tất` sau ACK.

### TC_10

Dùng test server điều tiết trong `test_target_tcp_integration.py`. Test health-check đo đúng 3/3 slot, kiểm tra client thứ tư bị từ chối và xác minh file kế tiếp vẫn chạy sau một lỗi.

### TC_12

Chạy server trên port khác, ví dụ:

```powershell
.\.venv\Scripts\python.exe Code\server.py --host 127.0.0.1 --port 19123 --dir uploads-test
```

Nhập `127.0.0.1` / `19123` trên client, bấm **Kiểm tra kết nối**, rồi upload. Khi queue còn tệp chờ/đang tải, hai ô endpoint bị khóa; sau khi queue kết thúc chúng được mở lại. Không dùng kết quả localhost để khẳng định LAN.

Ảnh UI (Windows desktop session):

```powershell
$env:QT_QPA_PLATFORM='windows'
.\.venv\Scripts\python.exe -B Code\tests\capture_ui_evidence.py
```

## MySQL tùy chọn

Module ở `Code\mysql_database`. Sao chép `.env.example` thành `.env` cục bộ và điền credential ngoài source. Không commit `.env`, dump, log hoặc dữ liệu upload thật. Migration `001_create_upload_history.sql` chỉ tạo bảng nếu chưa tồn tại và không chứa `DROP`, `TRUNCATE` hay BLOB.

## Dữ liệu không được commit

`.env`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `*.pyc`, `*.log`, `uploads/`, `*.part`, database dump, `config.json` chứa cấu hình cục bộ và lịch sử người dùng thật.
