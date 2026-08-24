# Thiết lập MySQL cho UDM_10

## 1. Yêu cầu

- MySQL Server 8.0 trở lên.
- Database mặc định: `udm_10`.
- Encoding: `utf8mb4` để lưu tên file Unicode.
- File vật lý không lưu trong MySQL; server tiếp tục ghi vào `UPLOAD_DIR`.

## 2. Chạy migration

Đăng nhập bằng tài khoản quản trị migration:

```powershell
mysql -u root -p
```

Sau đó chạy trong MySQL client:

```sql
SOURCE D:/UDM/database/migrations/001_create_upload_history.sql;
```

Migration có thể chạy lặp lại vì dùng `IF NOT EXISTS`. Migration không chứa
`DROP DATABASE`, `DROP TABLE`, `TRUNCATE` hoặc `DELETE`.

## 3. Tài khoản runtime

Khuyến nghị tạo tài khoản riêng và chỉ cấp quyền cần thiết. Thay các placeholder
trước khi chạy trực tiếp trong MySQL:

```sql
CREATE USER IF NOT EXISTS 'udm_app'@'127.0.0.1'
IDENTIFIED BY '<mat-khau-rieng-manh>';

GRANT SELECT, INSERT, UPDATE
ON `udm_10`.* TO 'udm_app'@'127.0.0.1';
```

Không ghi mật khẩu thật vào source, `.env.example`, tài liệu hoặc commit.

## 4. Cấu hình cục bộ

Sao chép `.env.example` thành `.env` và điền thông tin tại máy triển khai:

```dotenv
MYSQL_ENABLED=true
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=udm_10
MYSQL_USER=udm_app
MYSQL_PASSWORD=<mat-khau-cuc-bo>
```

`.env` đã nằm trong `.gitignore`. Khi `MYSQL_ENABLED=false`, server dùng
`HISTORY_JSON_PATH` (mặc định `database/history.json`). JSON được ghi UTF-8 bằng
file tạm và atomic replace.

## 5. Kiểm tra khởi động

```powershell
python run_server.py
```

Khi MySQL được bật, server kết nối và kiểm tra đủ ba bảng trước khi bind cổng
TCP. Nếu kết nối hoặc schema không sẵn sàng, tiến trình trả mã `2` và log một lỗi
rõ ràng nhưng không in mật khẩu.

## 6. Sao lưu

Chỉ sao lưu metadata khi được phép. Không đưa dump thật vào repository. Không
dùng lệnh phá hủy trong quy trình setup hoặc kiểm thử của dự án.

## 7. Kiểm tra schema và chuyển backend

Schema tối thiểu gồm `upload_batches`, `upload_files`, `upload_events`. Không có
cột BLOB. Để quay về JSON, dừng server, đặt `MYSQL_ENABLED=false` rồi khởi động
lại; không cần và không được xóa database.

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
python -m pytest tests\integration\test_history_persistence.py -q
```

Test dùng fake connector/JSON temp; không sửa database thật.
