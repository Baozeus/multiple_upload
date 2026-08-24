# Database UDM_10

MySQL chỉ lưu metadata và lịch sử upload. Dữ liệu binary vẫn nằm trong thư mục
`uploads` do server quản lý; schema không có cột `BLOB`.

## Nội dung

- `migrations/001_create_upload_history.sql`: tạo database `udm_10` và ba bảng
  `upload_batches`, `upload_files`, `upload_events`.
- `seeds/README.md`: chính sách seed an toàn.

Migration chỉ dùng `CREATE ... IF NOT EXISTS`; không chứa `DROP`, `TRUNCATE`,
`DELETE` hoặc thao tác xóa dữ liệu. Xem hướng dẫn tại
[`../docs/mysql-setup.md`](../docs/mysql-setup.md).
