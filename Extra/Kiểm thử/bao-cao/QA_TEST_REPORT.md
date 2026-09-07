# Báo cáo kiểm thử UDM_10 — Multiple Upload

- Thời điểm chạy: `2026-09-07T22:59:47+07:00`
- Kết luận: **PASS**
- Regression: **17 test — PASS**
- Functional: **15/15 PASS**
- Stress/performance: **2 mức tải**, không có lỗi

## Phạm vi và tiêu chí

Kiểm thử đi qua UI PySide6, TCP Client–Server và kết quả file trên filesystem. Functional đạt khi hành vi quan sát được đúng yêu cầu. Stress/performance đạt về độ tin cậy khi mọi Client hoàn tất, dữ liệu đúng SHA-256 và tỷ lệ lỗi bằng 0%. Đề tài chưa quy định SLA thời gian nên latency/throughput được ghi nhận làm baseline.

## Cấu hình máy và môi trường

| Thuộc tính | Giá trị |
|---|---|
| hostname | MSI |
| operating_system | Windows-11-10.0.26200-SP0 |
| cpu | 11th Gen Intel(R) Core(TM) i5-11400H @ 2.70GHz |
| logical_cpu_count | 12 |
| physical_memory_gib | 7.71 |
| python | 3.12.14 |
| python_executable | D:\UDM\.venv\Scripts\python.exe |
| transport | TCP loopback 127.0.0.1 |
| server_model | Một thread cho mỗi kết nối |
| git_commit | e1ae3e5f3f6d990351b17360d4e3db53b2afb950 |

## Kết quả test hồi quy

| Bộ test | Số test | Kết quả | Thời gian (giây) | Log |
|---|---:|---:|---:|---|
| `unittest discover -s Code/tests` | 17 | **PASS** | 0.602622 | `regression-tests.log` |

## Dữ liệu đầu vào và cách thực hiện

- Functional: file nhỏ cho 6 định dạng hợp lệ; file 1 MiB cho progress; header thiếu trường, dung lượng âm, `.exe`, đường dẫn không tồn tại và tên traversal.
- Mất kết nối: khai báo file 4 MiB, chỉ gửi một phần rồi đóng socket đột ngột; kiểm tra không có file hoàn chỉnh hoặc `.part` còn sót.
- Performance: mỗi Client gửi một file dữ liệu nhị phân xác định qua TCP loopback; các Client bắt đầu đồng thời bằng barrier.
- Xác minh: trạng thái TCP, nội dung/size/SHA-256 file đích, tiến trình UI và lịch sử JSON.

## Kết quả functional

| ID | Kịch bản | Kết quả | Thời gian (giây) | Chi tiết |
|---|---|---:|---:|---|
| F01 | Kéo-thả qua UI, upload TCP, tiến trình và lịch sử | **PASS** | 0.513029 | {"window_title": "Multiple Upload — UDM_10", "status": "Hoàn tất", "progress_percent": 100, "saved_file": "ui-dropped.txt", "history_records": 1, "screenshot": "ui-upload-completed.png"} |
| F02 | Upload đủ định dạng được hỗ trợ | **PASS** | 0.142349 | {"formats": [".txt", ".pdf", ".jpg", ".jpeg", ".doc", ".docx"], "count": 6} |
| F03 | Báo tiến trình riêng cho file | **PASS** | 0.049730 | {"samples": 16, "final_percent": 100} |
| F04 | Xử lý trùng tên rename/overwrite/skip | **PASS** | 0.049352 | {"rename": "conflict(1).txt", "overwrite": "SUCCESS", "skip": "SKIPPED"} |
| F05 | Từ chối định dạng không hợp lệ | **PASS** | 0.006658 | {"rejected": "blocked.exe", "message": "Định dạng không được hỗ trợ (.txt, .pdf, .jpg, .jpeg, .doc, .docx)."} |
| F06 | Từ chối file không tồn tại | **PASS** | 0.001115 | {"rejected": "missing.txt", "message": "Không tìm thấy tệp nguồn."} |
| F07 | Từ chối chính sách trùng tên sai | **PASS** | 0.003816 | {"policy": "invalid", "message": "Chính sách trùng tên không hợp lệ."} |
| F08 | Server từ chối header thiếu dữ liệu | **PASS** | 0.004958 | {"server_status": "ERROR", "message": "Thiếu filename hoặc filesize"} |
| F09 | Server từ chối dung lượng âm | **PASS** | 0.027940 | {"server_status": "ERROR", "message": "filesize phai >= 0"} |
| F10 | Chặn path traversal trong tên file | **PASS** | 0.029095 | {"input_name": "../escape.txt", "saved_as": "escape.txt"} |
| F11 | Ngắt kết nối đột ngột và dọn file tạm | **PASS** | 0.005936 | {"declared_bytes": 4194304, "sent_bytes": 49152, "partial_files_remaining": 0} |
| F12 | Báo lỗi khi Server không sẵn sàng | **PASS** | 0.519394 | {"port": 64206, "message": "Kết nối TCP quá thời gian chờ. Hãy thử lại."} |
| F13 | Upload file rỗng hợp lệ | **PASS** | 0.011060 | {"bytes": 0, "progress": 100} |
| F14 | Hàng đợi FIFO giới hạn 3 upload đồng thời | **PASS** | 0.005652 | {"files_added": 5, "active_uploads": 3, "waiting_files": 2, "configured_limit": 3} |
| F15 | Một Client lỗi không làm dừng Client khác | **PASS** | 0.078745 | {"broken_client": "disconnected", "valid_client": "SUCCESS", "valid_bytes": 1048576} |

## Kết quả stress và performance

| Client đồng thời | Dung lượng/file (MiB) | Tổng (MiB) | Thời gian (s) | Throughput (MiB/s) | Req/s | Mean (ms) | P50 (ms) | P95 (ms) | Max (ms) | Lỗi |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 2 | 10 | 0.084507 | 118.333 | 59.166 | 81.574 | 81.698 | 82.92 | 82.92 | 0 (0.0%) |
| 20 | 2 | 40 | 0.397867 | 100.536 | 50.268 | 361.986 | 382.816 | 394.846 | 395.169 | 0 (0.0%) |

## Bằng chứng

Thư mục bằng chứng: `docs/test-evidence/20260907-225947`

- `functional-results.json`: kết quả chi tiết từng case.
- `regression-results.json` và `regression-tests.log`: kết quả 17 test có sẵn.
- `performance-results.json` và `.csv`: số liệu hai mức tải.
- `server-functional.log`: log functional và lỗi mất kết nối.
- `server-load-*.log`: log Server cho từng mức tải.
- `ui-upload-completed.png`: ảnh UI sau khi upload hoàn tất.
- `run-summary.log`: log điều phối toàn bộ lần chạy.
- `manifest-sha256.json`: mã kiểm tra tính toàn vẹn bằng chứng.

## Giới hạn

Kết quả performance chạy trên loopback của một máy, nên chưa bao gồm packet loss, băng thông hoặc độ trễ mạng thật. Khi demo qua LAN cần chạy lại cùng runner hoặc một công cụ tải tương đương trên hai máy và ghi riêng cấu hình mạng.
