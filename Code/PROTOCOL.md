# Giao thức TCP UDM_10

## Framing

Mọi control message dùng `[4-byte unsigned big-endian length][UTF-8 JSON object]`. `HEADER_MAX = 64 KiB`. Dữ liệu file được gửi nhị phân ngay sau phản hồi `OK` và đúng bằng `filesize` byte.

Server chỉ nhận các đuôi `.txt`, `.pdf`, `.jpg`, `.jpeg`, `.doc`, `.docx` và tối đa **500 KiB = 512.000 byte** mỗi tệp.

## Health-check

Client gửi:

```json
{"type":"health_check","protocol":"UDM_10","version":1}
```

Server hợp lệ trả:

```json
{
  "status":"HEALTHY",
  "protocol":"UDM_10",
  "version":1,
  "can_accept_upload":true,
  "active_uploads":0,
  "upload_limit":3
}
```

Health-check được xử lý trước semaphore upload. Nó không tạo reservation, `.part`, upload history hay lỗi upload. `HEALTHY` xác nhận đúng giao thức; `can_accept_upload=false` nghĩa là Server vẫn phản hồi nhưng hiện đã đủ slot.

## Upload

Header:

```json
{"filename":"tài-liệu.pdf","filesize":102400,"conflict":"ask"}
```

`conflict` hỗ trợ:

- `ask`: nếu tên đã tồn tại, Server trả `DUPLICATE` trước payload;
- `rename`: dành tên tăng dần `file(1).ext`, an toàn khi upload đồng thời;
- `overwrite`: ghi vào `.part`, chỉ `os.replace` file đích sau khi nhận đủ;
- `skip`: trả `SKIPPED` trước payload nếu đích tồn tại.

Client cũ không gửi `conflict` vẫn mặc định `rename`.

Phản hồi đầu:

- `OK`: đích đã được dành; Client bắt đầu gửi payload;
- `DUPLICATE`: cần hỏi người dùng, không gửi payload;
- `SKIPPED`: không gửi payload;
- `REJECTED`: Server đang đủ slot upload;
- `ERROR`: header/validation không hợp lệ.

Khi nhận đủ payload, Server commit nguyên tử và trả `SUCCESS`. Nếu thiếu payload, timeout hoặc mất kết nối, Server xóa `.part`, giải phóng reservation/semaphore và bảo toàn file cũ.

Sau khi client gửi đủ payload nhưng trước `SUCCESS`, UI vẫn giữ trạng thái `Đang tải` với thông báo **“Đang chờ Server xác nhận”**. `Hoàn tất` chỉ được đặt sau phản hồi `SUCCESS`.
