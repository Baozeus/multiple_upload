# Báo cáo tích hợp giao diện Client mới

## Phạm vi

Bản preview tích hợp giao diện PySide6 từ `ui-handoff/client` với TCP Server hiện hữu. Không thay đổi schema, database, lịch sử JSON hoặc API HTTP cũ. Không commit và không push Git.

## Module, Interface, Seam và Adapter

| Thành phần | Vai trò |
|---|---|
| `UploadCoordinator` | Module điều phối queue, trạng thái và signal cho UI |
| `TcpUploadAdapter.upload(path, conflict, on_progress)` | Interface nhỏ tại seam transport; một lời gọi xử lý trọn vòng đời upload một file |
| `TcpUploadAdapter` | Adapter mặc định, dùng TCP framing hiện hữu |
| HTTP code trong `UploadCoordinator._start_http_upload` | HTTP Adapter tương thích cấu hình cũ |
| `UploadQueue` | Module FIFO, validation đầu vào và giới hạn đồng thời |
| `save_incoming_file` | Module lưu file tạm và commit nguyên tử trên Server |

UI không mở socket trực tiếp. Queue không biết TCP hoặc HTTP. Server không phụ thuộc PySide6.

## Mapping file

| File giao diện/logic | File đích | Cách tích hợp | Rủi ro/ghi chú |
|---|---|---|---|
| `ui-handoff/client/run.py` | Giữ nguyên | Entry point giao diện mới | Cần PySide6 6.9.1 |
| `main_window.py` | Sửa tại chỗ trong bản preview | Thêm trạng thái transport và lựa chọn conflict | Không đổi cấu trúc lịch sử |
| `uploader.py` | Sửa tại chỗ trong bản preview | TCP mặc định, HTTP và mock giữ tương thích | HTTP runtime chưa smoke test vì máy chưa có PySide6 |
| `tcp_transport.py` | File mới | Adapter TCP thuần Python, chạy nền qua signal Qt | Một kết nối cho mỗi file |
| `config.py` | Sửa tại chỗ trong bản preview | Mở rộng cấu hình, mặc định TCP | `config.json` cũ vẫn đọc được |
| `queue_manager.py` | Sửa tại chỗ trong bản preview | Validation 6 định dạng, giới hạn 10 GB | Tệp bị từ chối không vào queue |
| `Code/protocol.py` | Sửa tương thích ngược | Validation Server và field `conflict` tùy chọn | Client cũ mặc định rename |
| `Code/upload_handler.py` | Sửa tương thích | Ghi file tạm, commit sau khi nhận đủ | Không đổi thư mục dữ liệu |
| `Code/duplicate_handler.py` | Sửa tương thích | Reserve tên an toàn cho upload đồng thời | Overwrite thay file sau khi upload hoàn tất |
| `Code/server.py` | Sửa tương thích | Đọc conflict và trả `SKIPPED` khi cần | Không đổi framing TCP cũ |

## File giữ nguyên

- `history.py`, `models.py`: giữ cấu trúc record và trạng thái hiện hữu.
- `theme.py`: giữ visual system của UI handoff.
- `run.py`, `__main__.py`: giữ entry point.
- `mysql_database/`: không sử dụng và không thay đổi.
- Filesystem upload directory và JSON history: giữ nguyên.

## Hành vi sau tích hợp

- Kéo-thả hoặc chọn nhiều file.
- FIFO, mặc định tối đa 3 file cùng lúc, cấu hình được từ 1 đến 6.
- Trạng thái và tiến trình riêng từng file; TCP tính tốc độ từ byte thực tế.
- Một thread/kết nối cho mỗi file nên lỗi được cô lập.
- Người dùng chọn Đổi tên, Ghi đè hoặc Bỏ qua trên thanh danh sách.
- Ghi đè dùng file `.part` cùng filesystem và chỉ thay file đích sau khi nhận hoàn chỉnh.
- TCP mặc định; HTTP chỉ được chọn bằng cấu hình.
- Không tự báo thành công giả khi TCP mất kết nối.

## Kết quả kiểm tra

Lệnh:

```powershell
python -B -m unittest discover -s tests -v
```

Kết quả: **17/17 test pass**.

Đã kiểm tra:

- TCP upload thật đến `FileUploadServer`.
- Client cũ không gửi `conflict` vẫn rename.
- Rename, overwrite và skip.
- File tạm được dọn khi stream lỗi; file cũ không bị mất.
- Sáu định dạng cho phép và biên dung lượng đúng 10 GB.
- Queue FIFO và giới hạn đồng thời.
- Queue Client Tkinter cũ đưa file mới vào FIFO trước khi cấp worker.
- Cấu hình TCP mặc định và URL contract của HTTP Adapter.
- Cấu hình HTTP cũ chỉ có `base_url` vẫn tiếp tục chọn HTTP Adapter.
- Reservation được giải phóng nếu không thể tạo file tạm.

## Chưa kiểm tra được

- Không khởi chạy/raster giao diện PySide6 vì môi trường hiện tại chưa cài dependency `PySide6==6.9.1`.
- HTTP multipart runtime chưa có HTTP Server phù hợp trong repository để smoke test đầu-cuối.
- Chưa chạy upload file thật gần 10 GB; test dùng validation tại đúng biên kích thước.

## Hướng dẫn chạy preview

```powershell
cd D:\Download\multiple_upload-main\multiple_upload-main
python -m pip install -r ui-handoff\client\requirements.txt
python Code\server.py --host 127.0.0.1 --port 9000
python ui-handoff\client\run.py
```

Việc cài PySide6 chưa được thực hiện trong quá trình tạo preview.
