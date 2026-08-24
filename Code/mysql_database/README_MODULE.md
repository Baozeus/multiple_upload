# 07_mysql_database

## Chức năng module

MySQL metadata repository, migration an toàn, seed policy và cấu hình mẫu.

## Interface cung cấp

MySqlHistoryRepository và schema upload_batches/upload_files/upload_events.

## Dependency cần có

00_shared_contracts; mysql-connector-python

## File cần sao chép vào dự án tổng

Giữ nguyên cột Vị trí khi ghép trong MODULE_MANIFEST.md. Không ghi đè mặc định;
nếu file đích tồn tại, leader phải so sánh nội dung trước.

## Cách kiểm tra

Module này là gói bàn giao không được bật trong runtime mặc định. Test import
phụ thuộc `00_shared_contracts`; chỉ chạy sau khi nhóm tích hợp dependency đó.
Không kết nối MySQL hoặc chạy migration khi chỉ kiểm tra cấu trúc repository.

## Điều kiện hoàn thành

- Import công khai không lỗi.
- Test module đạt.
- Không định nghĩa lại contract production.
- Không thay business rule UDM_10.
- Không phát sinh collision khác nội dung.

## Cần xác nhận

Credential triển khai do leader cung cấp ngoài Git.
