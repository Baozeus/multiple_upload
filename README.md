# UDM_10 — Multiple Upload

Ứng dụng desktop Python cho phép **kéo-thả/chọn nhiều file và upload lên Server qua TCP**, có hàng đợi FIFO, giới hạn số file upload đồng thời, hiển thị tiến trình/tốc độ riêng cho từng file và xử lý file trùng tên.

## 1. Thành viên

- Nguyễn Tấn Bão
- Nguyễn Phi Long
- Nguyễn Viết Thịnh
- Nguyễn Đặng Xuân Phát
- Phạm Trần Đức Phú
- Phạm Ngọc Phú

## 2. Công nghệ

- Python 3.10+
- PySide6: giao diện Client
- TCP Socket: giao tiếp Client–Server
- Python Standard Library: Server, protocol và xử lý file
- unittest: kiểm thử
- Filesystem: nơi Server lưu file
- MySQL: module bàn giao riêng, **không dùng trong runtime mặc định**

## 3. Kiến trúc thực tế

<img width="1162" height="522" alt="Untitled Diagram drawio" src="https://github.com/user-attachments/assets/55bf1173-e9b5-4b05-8805-4970a5850723" />

**Lưu ý:** giới hạn `N = 3` hiện được thực thi ở **Client Queue**. Server hiện chấp nhận nhiều connection và tạo một thread cho mỗi connection; Server không có limiter N=3 riêng.

## 4. Luồng upload

1. Người dùng kéo-thả hoặc chọn nhiều file.
2. Client tạo `UploadItem` và đưa vào queue.
3. Queue lấy file theo thứ tự FIFO.
4. Khi còn slot, Coordinator tạo worker upload.
5. Mỗi file mở **một TCP connection riêng**.
6. Client gửi header JSON rồi gửi dữ liệu nhị phân theo chunk.
7. Server kiểm tra tên, định dạng, kích thước và chính sách trùng tên.
8. Server ghi dữ liệu vào file tạm `.part`.
9. Khi nhận đủ dữ liệu, Server commit file và trả `SUCCESS`.
10. Client cập nhật `COMPLETED`; nếu lỗi chỉ file đó chuyển `ERROR`, sau đó queue cấp slot cho file tiếp theo.

## 5. State machine

<img width="392" height="312" alt="1" src="https://github.com/user-attachments/assets/bf3c94a2-0e7d-4eff-ad0a-1ad6c2793726" />

## 6. Quy tắc file

- Định dạng: `.txt`, `.pdf`, `.jpg`, `.jpeg`, `.doc`, `.docx`
- Kích thước tối đa: 10 GB/file
- Tên file được kiểm tra để tránh path traversal
- Trùng tên:
  - `rename`: `file.txt` -> `file(1).txt` -> `file(2).txt`...
  - `overwrite`: ghi đè file đích
  - `skip`: bỏ qua file đã tồn tại
- Upload lỗi không làm dừng các file khác.
- File chưa hoàn thành không được commit thành file đích; dữ liệu tạm dùng đuôi `.part`.

## 7. TCP Protocol

Chi tiết xem `Code/PROTOCOL.md`.

Tóm tắt:

```text
Client -> Server
[4 byte big-endian length][JSON header][binary file data]

Server -> Client
[4 byte big-endian length][JSON response]
```

Header:

```json
{
  "filename": "tailieu.pdf",
  "filesize": 102400,
  "conflict": "rename"
}
```

Phản hồi mở đầu:

```json
{"status": "OK", "saved_as": "tailieu.pdf"}
```

Phản hồi thành công:

```json
{"status": "SUCCESS", "saved_as": "tailieu.pdf", "bytes": 102400}
```

## 8. Cấu trúc thư mục

```text
multiple_upload-main/
├── README.md
├── Code/
│   ├── server.py
│   ├── protocol.py
│   ├── upload_handler.py
│   ├── duplicate_handler.py
│   ├── requirements.txt
│   ├── PROTOCOL.md
│   ├── tests/
│   ├── ui-handoff/
│   │   └── client/
│   │       ├── run.py
│   │       ├── requirements.txt
│   │       └── multiple_upload_client/
│   │           ├── main_window.py
│   │           ├── queue_manager.py
│   │           ├── uploader.py
│   │           ├── tcp_transport.py
│   │           ├── config.py
│   │           ├── models.py
│   │           └── ...
│   └── mysql_database/
├── DOCX/
│   ├── UDM_10_Bao_cao_cap_nhat.docx
│   └── HUONG_DAN_KHOI_CHAY.md
├── PPTX/
└── Extra/
```

## 9. Cài đặt và chạy

Yêu cầu Windows 10/11 và Python 3.10+.

Từ thư mục gốc:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r Code\ui-handoff\client\requirements.txt
```

Nếu PowerShell chặn kích hoạt môi trường:

```powershell
.\.venv\Scripts\python.exe -m pip install -r Code\ui-handoff\client\requirements.txt
```

### Terminal 1 — Server

```powershell
python Code\server.py --host 127.0.0.1 --port 9000 --dir uploads
```

### Terminal 2 — Client

```powershell
python Code\ui-handoff\client\run.py
```

Client mặc định dùng:

- TCP
- `127.0.0.1:9000`
- tối đa 3 file upload đồng thời
- conflict policy `rename`

## 10. Kiểm thử

```powershell
python -B -m unittest discover -s Code\tests -v
```

TCP smoke test:

```powershell
python -B -m unittest Code.tests.test_tcp_smoke -v
```

Protocol/storage:

```powershell
python -B -m unittest Code.tests.test_protocol_and_storage -v
```

## 11. Ghi chú quan trọng

Kiến trúc trong bản cập nhật này được đồng bộ theo **source code hiện tại**: Client là **PySide6 + TCP**, không phải Tkinter + Flask/HTTP. HTTP Adapter vẫn tồn tại trong Client để tương thích cấu hình cũ, nhưng không phải đường chạy mặc định và repository không kèm HTTP Server tương ứng.

MySQL nằm trong module `Code/mysql_database/` và không được khởi động trong demo TCP mặc định.
