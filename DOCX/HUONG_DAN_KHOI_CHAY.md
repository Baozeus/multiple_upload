# Hướng dẫn khởi chạy UDM_10 — Multiple Upload

Tài liệu này tổng hợp các cách khởi chạy project từ **thư mục gốc repository** — thư mục chứa `README.md` và `Code/`.

## 1. Thành phần có thể chạy

| Thành phần | Entry point | Mục đích |
|---|---|---|
| TCP Server | `Code/server.py` | Nhận file qua TCP và lưu vào filesystem |
| Client PySide6 | `Code/ui-handoff/client/run.py` | Giao diện chính, dùng TCP mặc định |
| Client Tkinter cũ | `Code/client.py` | Giao diện cũ để kiểm tra tương thích TCP |
| HTTP Adapter | Tích hợp trong Client PySide6 | Kết nối tới HTTP Server cũ nếu có |
| Mock transport | Tích hợp trong Client PySide6 | Xem và thử giao diện mà không cần Server |
| Test suite | `Code/tests/` | Unit test và TCP smoke test |

Project mặc định **không sử dụng MySQL**. Dữ liệu upload được lưu trên filesystem; lịch sử của Client PySide6 được lưu trong file JSON cục bộ.

## 2. Yêu cầu môi trường

- Windows 10/11.
- Python 3.10 trở lên; khuyến nghị Python 3.11 hoặc 3.12.
- Port TCP mặc định: `9000`.
- Client PySide6 cần dependency trong `Code/ui-handoff/client/requirements.txt`.

Kiểm tra Python:

```powershell
python --version
python -m pip --version
```

Nếu lệnh `python` mở Microsoft Store hoặc báo không tìm thấy, hãy cài Python từ trang chính thức và chọn **Add Python to PATH**, hoặc dùng đường dẫn đầy đủ tới `python.exe` đã cài trên máy.

## 3. Chuẩn bị môi trường ảo — khuyến nghị

Chạy tại thư mục gốc repository:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r Code\ui-handoff\client\requirements.txt
```

Nếu PowerShell chặn script kích hoạt, có thể không kích hoạt và gọi Python trực tiếp:

```powershell
.\.venv\Scripts\python.exe -m pip install -r Code\ui-handoff\client\requirements.txt
```

Không commit `.venv/`, file cấu hình riêng, lịch sử upload hoặc dữ liệu upload lên Git.

## 4. Cách 1 — Chạy đầy đủ TCP Server và giao diện mới

Đây là cách chạy chính thức và được khuyến nghị.

### Terminal 1 — TCP Server

```powershell
python Code\server.py --host 127.0.0.1 --port 9000 --dir uploads
```

Ý nghĩa tham số:

- `--host 127.0.0.1`: chỉ cho Client trên cùng máy kết nối.
- `--host 0.0.0.0`: cho phép máy khác trong cùng mạng kết nối; cần cấu hình firewall phù hợp.
- `--port 9000`: port TCP; giá trị hợp lệ từ 1 đến 65535.
- `--dir uploads`: thư mục lưu file trên Server.

### Terminal 2 — Client PySide6

```powershell
python Code\ui-handoff\client\run.py
```

Khi không có `config.json`, Client tự dùng:

- Transport: `tcp`.
- Server: `127.0.0.1:9000`.
- Tối đa 3 file upload đồng thời.
- File trùng tên: `rename` — tự đổi tên.

Trên giao diện, chọn chính sách **Đổi tên**, **Ghi đè** hoặc **Bỏ qua**, sau đó kéo-thả hoặc chọn nhiều file.

Các định dạng được hỗ trợ: `.txt`, `.pdf`, `.jpg`, `.jpeg`, `.doc`, `.docx`. Dung lượng tối đa là 10 GB cho mỗi file.

## 5. Cách 2 — Chạy TCP bằng cấu hình riêng

Sao chép file cấu hình mẫu:

```powershell
Copy-Item Code\ui-handoff\client\config.example.json Code\ui-handoff\client\config.json
```

Ví dụ nội dung `Code/ui-handoff/client/config.json`:

```json
{
  "transport": "tcp",
  "tcp_host": "127.0.0.1",
  "tcp_port": 9000,
  "base_url": "",
  "upload_endpoint": "/api/uploads",
  "allow_mock_fallback": false,
  "max_concurrent": 3,
  "conflict_policy": "rename"
}
```

Sau đó chạy Server và Client như Cách 1. Không đưa `config.json` có cấu hình máy cá nhân hoặc thông tin nhạy cảm lên Git.

## 6. Cách 3 — Cấu hình nhanh bằng biến môi trường

Biến môi trường có độ ưu tiên cao hơn `config.json`.

```powershell
$env:UDM10_TRANSPORT = "tcp"
$env:UDM10_TCP_HOST = "127.0.0.1"
$env:UDM10_TCP_PORT = "9000"
$env:UDM10_MAX_CONCURRENT = "3"
$env:UDM10_CONFLICT_POLICY = "rename"
python Code\ui-handoff\client\run.py
```

Giá trị hợp lệ:

- `UDM10_TRANSPORT`: `tcp`, `http` hoặc `mock`.
- `UDM10_MAX_CONCURRENT`: từ 1 đến 6.
- `UDM10_CONFLICT_POLICY`: `rename`, `overwrite` hoặc `skip`.

Biến môi trường chỉ tồn tại trong cửa sổ PowerShell hiện tại. Đóng cửa sổ để trở về cấu hình mặc định.

## 7. Cách 4 — Chỉ xem giao diện bằng Mock transport

Cách này không cần chạy TCP Server, phù hợp để trình bày bố cục và trạng thái giao diện. Nó không chứng minh dữ liệu đã được truyền qua mạng hoặc lưu trên Server.

```powershell
$env:UDM10_TRANSPORT = "mock"
python Code\ui-handoff\client\run.py
```

Sau khi xem xong:

```powershell
Remove-Item Env:UDM10_TRANSPORT
```

## 8. Cách 5 — Dùng HTTP Adapter tương thích cấu hình cũ

Repository hiện có HTTP Adapter phía Client, nhưng **không kèm HTTP Server để thay thế TCP Server**. Cách này chỉ dùng khi nhóm đã có một HTTP Server cũ tương thích với multipart upload.

```powershell
$env:UDM10_TRANSPORT = "http"
$env:UDM10_API_BASE_URL = "http://127.0.0.1:8000"
$env:UDM10_UPLOAD_ENDPOINT = "/api/uploads"
$env:UDM10_ALLOW_MOCK_FALLBACK = "false"
python Code\ui-handoff\client\run.py
```

HTTP Adapter gửi tới `base_url + upload_endpoint` và truyền chính sách file trùng bằng query `conflict`. Không dùng `Code/server.py` cho cách này vì `Code/server.py` là TCP Server, không phải HTTP Server.

## 9. Cách 6 — Chạy Client Tkinter cũ

Client cũ vẫn dùng TCP và mặc định không gửi field `conflict`; Server sẽ tương thích ngược và mặc định xử lý theo `rename`.

Client này import `tkinterdnd2`. Nếu môi trường chưa có thư viện đó:

```powershell
python -m pip install tkinterdnd2
```

Chạy Server ở Terminal 1:

```powershell
python Code\server.py --host 127.0.0.1 --port 9000 --dir uploads
```

Chạy Client cũ ở Terminal 2:

```powershell
python Code\client.py
```

Lưu ý: `Code/requirements.txt` hiện chưa khai báo chính xác dependency `tkinterdnd2`; giao diện PySide6 mới vẫn là Client được khuyến nghị.

## 10. Chạy test và smoke test

Chạy toàn bộ bộ test từ thư mục gốc:

```powershell
python -B -m unittest discover -s Code\tests -v
```

Chạy riêng TCP smoke test:

```powershell
python -B -m unittest Code.tests.test_tcp_smoke -v
```

Chạy riêng test protocol, validation và xử lý file trùng:

```powershell
python -B -m unittest Code.tests.test_protocol_and_storage -v
```

Bộ test không cần kết nối MySQL và không thay đổi database.

## 11. Quy trình demo đề xuất

1. Mở TCP Server bằng Cách 1.
2. Mở Client PySide6.
3. Thêm từ 4 file hợp lệ trở lên để quan sát giới hạn upload đồng thời và queue FIFO.
4. Kiểm tra trạng thái riêng của từng file: Chờ, Đang tải, Hoàn tất hoặc Lỗi.
5. Quan sát phần trăm và tốc độ upload từng file.
6. Upload lại một file với lần lượt ba chính sách: Đổi tên, Ghi đè và Bỏ qua.
7. Thử file sai định dạng để kiểm tra validation.
8. Tắt Server rồi thử upload để kiểm tra thông báo lỗi và nút Thử lại.
9. Mở lại Client để kiểm tra lịch sử JSON, tìm kiếm và lọc trạng thái.
10. Kiểm tra file nhận được trong thư mục `uploads/`.

## 12. Xử lý lỗi thường gặp

### `ModuleNotFoundError: No module named 'PySide6'`

```powershell
python -m pip install -r Code\ui-handoff\client\requirements.txt
```

Đảm bảo lệnh cài dependency và lệnh chạy Client dùng cùng một Python:

```powershell
python -c "import PySide6; print(PySide6.__version__)"
```

### `ModuleNotFoundError: No module named 'tkinterdnd2'`

Lỗi này chỉ liên quan Client Tkinter cũ. Cài `tkinterdnd2` hoặc dùng Client PySide6 mới.

### Không kết nối được `127.0.0.1:9000`

- Kiểm tra cửa sổ Server còn chạy.
- Kiểm tra Client và Server dùng cùng host/port.
- Kiểm tra port đang lắng nghe:

```powershell
Get-NetTCPConnection -LocalPort 9000 -State Listen
```

- Nếu port 9000 đang bị chiếm, chọn port khác cho cả Server và Client.

### File bị từ chối

- Kiểm tra phần mở rộng thuộc danh sách hỗ trợ.
- Kiểm tra dung lượng không vượt 10 GB.
- Kiểm tra tên file hợp lệ và chính sách xử lý file trùng.

### Dừng chương trình

- Đóng cửa sổ Client bình thường.
- Tại Terminal chạy Server, nhấn `Ctrl+C` để dừng.

## 13. Lệnh chạy nhanh nhất

Terminal 1:

```powershell
python Code\server.py --host 127.0.0.1 --port 9000 --dir uploads
```

Terminal 2:

```powershell
python Code\ui-handoff\client\run.py
```
