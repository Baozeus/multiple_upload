# CHANGELOG UDM — xác minh TC_3, TC_4, TC_9, TC_10, TC_12

Ngày kiểm chứng: 2026-09-24  
Source làm việc: `D:\UDM\UDM_FIXED`

## Baseline trước khi sửa

- Kiến trúc thực tế: PySide6 desktop client, mỗi tệp dùng một TCP connection, queue FIFO phía client và semaphore phía server.
- Suite hiện hữu: 39/39 test PASS.
- Chức năng nền đã có, nhưng chưa có bằng chứng TCP chậm cho 3+3, chưa có trạng thái chờ ACK và cấu hình mặc định vẫn ghi 10 GB.

## Nguyên nhân và thay đổi

### Giới hạn đã xác nhận

- Đồng bộ client/server về tối đa **3 upload đồng thời**.
- Giới hạn một lần thêm vẫn là **6 tệp hợp lệ**.
- Đồng bộ dung lượng tối đa thành **500 KiB = 512.000 byte**. Checklist gọi ngắn là “500 KB”; dự án dùng quy ước nhị phân KiB.
- Không cho cấu hình client nâng giới hạn vượt 512.000 byte.
- Gom giới hạn client vào `multiple_upload_client/limits.py` để queue, config và TCP adapter dùng chung.

### TC_3 và TC_4

- Giữ FIFO: 6 tệp chạy thành hai đợt 3 + 3.
- Batch 8 tệp hợp lệ chỉ tạo 6 `UploadItem`; 2 tệp cuối không vào queue và không có worker.
- Thông báo đúng: “Mỗi lần chỉ nhận tối đa 6 file. Đã nhận 6 file; 2 file còn lại chưa được thêm.”
- Quy tắc danh sách hỗn hợp: tệp không hợp lệ không tiêu thụ quota 6 tệp hợp lệ; sau khi đã nhận đủ 6, phần còn lại của lần thêm bị từ chối theo giới hạn batch.

### TC_9

- `TcpUploadAdapter.upload()` có callback riêng `on_waiting_for_ack` sau khi gửi đủ payload và trước khi đọc phản hồi cuối.
- Coordinator giữ trạng thái `Đang tải`, progress tối đa 99% và hiển thị “Đang chờ Server xác nhận” cho tới `SUCCESS`.
- Progress phía UI không giảm trong một lần thử; tốc độ âm, vô hạn hoặc NaN được chuẩn hóa thành `0 B/s`.
- Không thêm sleep vào production. Server đọc chậm/ACK trễ chỉ tồn tại trong test.

### TC_10

- Bổ sung extension point no-op `FileUploadServer.on_chunk_received()` để test server có thể điều tiết hoặc gây lỗi có kiểm soát; runtime production không chờ giả lập.
- Test TCP thật chứng minh health-check thấy `active_uploads=3`, không vượt 3, ba tệp còn lại chờ rồi tự chạy.
- Khi server đủ 3 slot, client ngoài bị từ chối theo chính sách `REJECTED` hiện hữu.
- Test lỗi một tệp chứng minh semaphore/queue giải phóng slot và tệp kế tiếp vẫn hoàn tất; không còn `.part`.

### TC_12

- Endpoint vẫn được kiểm tra theo port 1–65535 và health-check đúng giao thức UDM.
- Cấu hình IP/port bị khóa khi còn tệp `Chờ` hoặc `Đang tải`; do đó tệp đang chờ không âm thầm chuyển sang server khác.
- Mỗi worker chụp `(host, port)` một lần trước khi bắt đầu truyền.
- Kết quả kiểm tra kết nối cũ bị vô hiệu khi endpoint thay đổi.

## File/hàm chính

| File | Vùng thay đổi |
|---|---|
| `Code/protocol.py` | Giới hạn server 512.000 byte |
| `Code/server.py` | Test hook no-op sau mỗi chunk |
| `Code/ui-handoff/client/multiple_upload_client/limits.py` | Giới hạn client dùng chung |
| `config.py` | Mặc định và validation 3/512.000 |
| `queue_manager.py` | Batch 6, concurrency 3, lý do từ chối thống nhất |
| `tcp_transport.py` | Callback chờ ACK, giới hạn 500 KiB |
| `uploader.py` | Thông báo batch, progress monotonic, trạng thái ACK, khóa endpoint |
| `main_window.py`, `widgets.py` | Khóa ô endpoint khi queue chạy; hiển thị giới hạn |
| `Code/tests/test_target_tcp_integration.py` | TCP thật cho TC_3, TC_8, TC_10, TC_12 |
| Các test hiện hữu | Regression cho TC_4, TC_5, TC_9 và UI |

## Không thay đổi

- Không đổi framework, protocol framing, chính sách duplicate hoặc persistence.
- Không thêm Pause/Resume, HTTP backend hoặc auto-retry.
- Không chạy MySQL thật và không sửa dữ liệu thật.
