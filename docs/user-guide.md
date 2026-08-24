# Hướng dẫn sử dụng UDM_10

## Bắt đầu

Khởi động server trước, sau đó chạy client. Góc trên phải hiển thị **Đã kết
nối**. Nếu thấy **Mất kết nối**, kiểm tra server và chọn **Thử kết nối**.

## Tải tệp

1. Kéo một hoặc nhiều tệp vào vùng **Kéo và thả tệp vào đây**, hoặc chọn
   **Chọn tệp** và chọn nhiều tệp trong hộp thoại.
2. Theo dõi từng dòng: **Đang chờ**, **Đang tải**, **Hoàn tất**, **Lỗi** hoặc
   **Đã bỏ qua**. Mỗi file đang tải có phần trăm và tốc độ riêng.
3. Có thể cuộn danh sách dài; rê chuột lên tên bị rút gọn để xem tên đầy đủ.

## Tệp trùng tên

Ứng dụng không tự chọn:

- **Ghi đè**: thay đúng file hiện tại sau khi nhận đủ payload.
- **Đổi tên**: giữ file cũ, server tạo hậu tố `_1`, `_2`, ...
- **Bỏ qua**: không gửi payload, lưu trạng thái `skipped`.

**Ghi đè** là thao tác destructive và dùng nút cảnh báo. Có thể dùng
Tab/Shift+Tab, Space và Enter để điều hướng/chọn.

## Lịch sử

Mở **Lịch sử**, nhập tên vào ô tìm kiếm hoặc lọc theo trạng thái. Dữ liệu được
tải nền nên GUI không bị chặn. Khi lỗi, dùng **Thử lại**; khi không có kết quả,
xóa tìm kiếm và bộ lọc.

## Xử lý sự cố

| Hiện tượng | Xử lý |
|---|---|
| Mất kết nối | Chạy/kiểm tra server, chọn **Thử kết nối**, rồi thử lại file lỗi. |
| Sai định dạng/quá dung lượng | Xem cấu hình server; chọn file hợp lệ. |
| File lỗi riêng lẻ | Dùng **Thử lại** đúng dòng; các file khác vẫn tiếp tục. |
| Không tải được lịch sử | Kiểm tra JSON/MySQL và kết nối rồi chọn **Thử lại**. |

Ứng dụng không có Pause/Resume và không tự động retry.
