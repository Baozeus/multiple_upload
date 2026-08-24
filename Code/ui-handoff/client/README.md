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
  "conflict_policy": "rename"
}
```

Không có `config.json`, Client tự dùng TCP `127.0.0.1:9000`, tối đa 3 upload đồng thời và đổi tên khi trùng.

Các biến môi trường tương ứng:

- `UDM10_TRANSPORT=tcp|http|mock`
- `UDM10_TCP_HOST`, `UDM10_TCP_PORT`
- `UDM10_API_BASE_URL`, `UDM10_UPLOAD_ENDPOINT`
- `UDM10_ALLOW_MOCK_FALLBACK`
- `UDM10_MAX_CONCURRENT` (1–6)
- `UDM10_CONFLICT_POLICY=rename|overwrite|skip`

## Chạy

```powershell
python -m pip install -r Code/ui-handoff/client/requirements.txt
python Code/server.py --host 127.0.0.1 --port 9000
python Code/ui-handoff/client/run.py
```

Trong giao diện, chọn chính sách **Đổi tên**, **Ghi đè** hoặc **Bỏ qua** trước khi thêm file. Các tệp đang chờ sẽ nhận lựa chọn mới; tệp đang tải không bị thay đổi giữa chừng.

Định dạng được hỗ trợ: `.txt`, `.pdf`, `.jpg`, `.jpeg`, `.doc`, `.docx`. Dung lượng tối đa mỗi tệp là 10 GB.

## Tương thích

- Client TCP cũ không gửi `conflict` vẫn hoạt động; Server mặc định `rename`.
- TCP header mới chỉ bổ sung field tùy chọn `conflict`.
- HTTP multipart cũ vẫn dùng `base_url + upload_endpoint` và query `conflict`.
- Mock không tự kích hoạt khi TCP lỗi; chỉ dùng khi chủ động đặt `transport: "mock"` hoặc bật fallback cho HTTP.
- Lịch sử vẫn lưu ở JSON cục bộ như giao diện handoff ban đầu.
