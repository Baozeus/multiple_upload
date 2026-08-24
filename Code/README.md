# File Upload — Client–Server (Python TCP)

Ứng dụng desktop Python upload nhiều file qua TCP, đáp ứng yêu cầu đồ án: **không dùng Web App**, giao tiếp mạng thật bằng socket, GUI không bị treo khi tải.

## Kiến trúc

**Mô hình:** Client–Server đa luồng (multi-threaded).

| Thành phần | Vai trò |
|---|---|
| `server.py` | Process riêng: lắng nghe TCP, mỗi client connection = 1 thread xử lý 1 file |
| `client.py` | Process riêng: GUI Tkinter, hàng đợi file + tối đa 3 worker thread upload song song |
| `protocol.py` | Framing chung (4-byte length + JSON) và validate |

Demo bắt buộc chạy **hai process độc lập** (có thể trên cùng máy):

```text
Terminal 1:  python server.py --port 9000
Terminal 2:  python client.py
```

Client mở **một kết nối TCP cho mỗi file** (không chia sẻ một socket cho nhiều file).

## Protocol (TCP)

**Port mặc định:** `9000` (có thể đổi bằng `--port` trên server và ô Port trên GUI).

**Vòng đời kết nối (mỗi file):**

1. **Establish** — Client `connect(IP, Port)`.
2. **Header (JSON)** — Client gửi `4 bytes (big-endian length)` + JSON:
   ```json
   {"filename": "tailieu.pdf", "filesize": 1024500}
   ```
   Server validate (tên an toàn, filesize hợp lệ). Không hợp lệ → trả lỗi rõ ràng và đóng kết nối.
   Hợp lệ → `{"status": "OK", "saved_as": "..."}`.
3. **Data stream (binary)** — Client gửi file theo chunk `4096` bytes.
4. **Confirm** — Server trả `{"status": "SUCCESS", "saved_as": "file.txt", "bytes": N}`.
5. **Terminate** — Đóng socket hai phía.

**Trùng tên:** TCP header hỗ trợ field tùy chọn `conflict` với ba giá trị `rename`, `overwrite`, `skip`. Client cũ không gửi field này vẫn hoạt động và mặc định `rename`. Khi đổi tên, `file.txt` lần lượt thành `file(1).txt`, `file(2).txt`, …

**Validation:** chỉ nhận `.txt`, `.pdf`, `.jpg`, `.jpeg`, `.doc`, `.docx`; tối đa 10 GB mỗi file.

**Timeout / mất mạng:** `socket.settimeout(5)`. Server bắt exception, **xóa file tạm `.part` chưa hoàn chỉnh**, rồi đóng socket.

## State Machine (mỗi file trên Client)

```text
[Kéo thả / chọn file]
        │
        ▼
    PENDING ──(cấp worker thread)──► UPLOADING ──(SUCCESS)──► COMPLETED
                                        │
                                        └──(mất mạng / timeout / từ chối)──► ERROR
```

- `PENDING`: trong hàng đợi, chờ slot (tối đa 3 upload đồng thời).
- `UPLOADING`: worker đọc file, gửi TCP; GUI cập nhật % và KB/s–MB/s.
- `COMPLETED`: server xác nhận; giải phóng worker.
- `ERROR`: chỉ ảnh hưởng file đó; các file khác vẫn tiếp tục.

## Giao diện Client

1. **Cấu hình mạng** — IP, Port (không hard-code), nút Connect/Check.
2. **Drag & Drop** — khung viền đứt nét (hoặc nút Chọn file).
3. **Bảng file** — Tên | Kích thước | Trạng thái | Progress | Tốc độ.

## Cài đặt & chạy

Chỉ cần Python (stdlib: `socket`, `threading`, `tkinter`) — không cài thêm thư viện.

```bash
cd UML-10

# Terminal 1 — Server
python server.py --host 0.0.0.0 --port 9000 --dir uploads

# Terminal 2 — Client
python client.py
```

Trên Client: nhập IP (`127.0.0.1` nếu cùng máy), Port `9000` → **Connect/Check** → **Chọn file**.

File nhận được nằm trong thư mục `uploads/`.

## Cấu trúc thư mục

```text
UML-10/
├── protocol.py        # Framing + validation chung
├── server.py          # Server đa luồng
├── client.py          # GUI Client + state machine
├── requirements.txt
├── README.md
└── uploads/           # Tạo khi chạy server
```
