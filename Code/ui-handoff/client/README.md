# Client giao diện mới (PySide6)

Giao diện trong thư mục này là Client chính. Client dùng TCP mặc định để tương thích trực tiếp với `Code/server.py`; HTTP Adapter cũ vẫn được giữ lại và chỉ hoạt động khi cấu hình `transport: "http"`.

## Cấu hình

Sao chép `config.example.json` thành `config.json` nếu cần đổi giá trị mặc định:

```json
{
  "transport": "tcp",
  "tcp_host": "127.0.0.1",
  "tcp_port": 9000,
  "base_url": "",
  "upload_endpoint": "/api/uploads",
  "allow_mock_fallback": false,
  "max_concurrent": 3,
  "max_upload_size": 512000,
  "conflict_policy": "ask"
}
```

Không có `config.json`, Client tự dùng TCP `127.0.0.1:9000`, tối đa 3 upload đồng thời và hỏi người dùng khi thật sự trùng tên.

Các biến môi trường tương ứng:

- `UDM10_TRANSPORT=tcp|http|mock`
- `UDM10_TCP_HOST`, `UDM10_TCP_PORT`
- `UDM10_API_BASE_URL`, `UDM10_UPLOAD_ENDPOINT`
- `UDM10_ALLOW_MOCK_FALLBACK`
- `UDM10_MAX_CONCURRENT` (1–3)
- `UDM10_MAX_UPLOAD_SIZE` (byte)
- `UDM10_CONFLICT_POLICY=ask|rename|overwrite|skip`

## Chạy

```powershell
python -m pip install -r Code/ui-handoff/client/requirements.txt
python Code/server.py --host 127.0.0.1 --port 9000
python Code/ui-handoff/client/run.py
```

Trong giao diện, khi Server xác nhận tên tệp đã tồn tại, dialog sẽ yêu cầu chọn **Đổi tên**, **Ghi đè** hoặc **Bỏ qua** cho riêng tệp đó. Không có lựa chọn ngầm trước khi phát hiện trùng tên; tác vụ đang tải không bị đổi policy giữa chừng.

Vùng cấu hình TCP có nút **Kiểm tra kết nối**. Nút này xác thực health-check UDM, chạy ngoài GUI thread, có timeout và không tạo file/history hay chiếm slot upload.

Định dạng được hỗ trợ: `.txt`, `.pdf`, `.jpg`, `.jpeg`, `.doc`, `.docx`. Dung lượng tối đa mỗi tệp là **500 KiB (512.000 byte)**; đây là giá trị “500 KB” trong checklist, diễn giải theo quy ước nhị phân.

## Tương thích

- Client TCP cũ không gửi `conflict` vẫn hoạt động; Server mặc định `rename`.
- TCP header mới chỉ bổ sung field tùy chọn `conflict`.
- HTTP multipart cũ vẫn dùng `base_url + upload_endpoint` và query `conflict`.
- Mock không tự kích hoạt khi TCP lỗi; chỉ dùng khi chủ động đặt `transport: "mock"` hoặc bật fallback cho HTTP.
- Lịch sử vẫn lưu ở JSON cục bộ như giao diện handoff ban đầu.
