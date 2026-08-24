# Kế hoạch triển khai UDM_10 - Upload nhiều file

## 1. Phạm vi dự án

### 1.1. Mục tiêu

Xây dựng ứng dụng Python GUI theo mô hình client-server, cho phép người dùng thêm một hoặc nhiều file bằng kéo-thả hoặc hộp thoại chọn file, đưa file vào hàng đợi và upload lên server với trạng thái, tiến trình và tốc độ độc lập cho từng file.

Toàn bộ source code, cấu hình, tài liệu, metadata/history runtime, test và vùng lưu file upload của dự án phải nằm trong `D:\UDM`.

### 1.2. Nguồn yêu cầu và thứ tự ưu tiên

1. `D:\Download\udm.jpg`: đề bài gốc, là nguồn xác định phạm vi bắt buộc.
2. `D:\Download\UDM_10_TestCase - Trang tính1.pdf`: checklist kiểm thử, dùng để nhận diện yêu cầu mở rộng và tiêu chí chấp nhận.
3. `D:\Download\KeHoach_NhanSu_UDM10_DenTrang (1).docx`: kế hoạch nhân sự, vai trò và lộ trình phối hợp.

Nếu checklist hoặc kế hoạch nhân sự bổ sung hành vi không xuất hiện trong đề gốc, hành vi đó được đánh dấu là yêu cầu mở rộng và chưa mặc nhiên trở thành yêu cầu bắt buộc.

Prompt hiện tại của dự án là nguồn xác nhận phạm vi. Khi một nội dung vốn chỉ xuất hiện trong checklist nhưng được prompt hiện tại nêu lại trong phần "Yêu cầu cốt lõi", nội dung đó được xem là **đã xác nhận trong dự án**.

### 1.3. Yêu cầu bắt buộc từ đề bài

- Thông tin quản lý đề bài: Project Code `UDM_10`, số nhóm tối đa `2` (đây không phải giới hạn upload đồng thời `N`).
- GUI cho phép kéo-thả một hoặc nhiều file vào vùng upload.
- Mỗi file có trạng thái riêng theo luồng cốt lõi: `Chờ -> Đang tải -> Hoàn tất` hoặc `Lỗi`.
- Hiển thị tiến trình phần trăm và tốc độ upload riêng cho từng file.
- Có hàng đợi hoặc upload đồng thời, nhưng phải giới hạn số file đang upload cùng lúc.
- Lỗi của một file không được làm dừng hoặc làm sai trạng thái các file còn lại.
- Server phải có quy tắc xử lý file trùng tên.
- Pause/Resume không bắt buộc và không nằm trong phạm vi UDM_10.

### 1.4. Yêu cầu mở rộng từ checklist

- Thêm file qua nút chọn file, hỗ trợ chọn một hoặc nhiều file.
- Validation phía client trước khi upload: định dạng, dung lượng tối đa, file 0 byte và thông báo lỗi rõ ràng.
- Hiển thị đúng tên dài, tiếng Việt và Unicode; danh sách nhiều file phải cuộn được và không vỡ bố cục.
- API xử lý upload một hoặc nhiều file, trả kết quả riêng cho từng file và trả lỗi rõ ràng khi request thiếu dữ liệu.
- Hàng đợi tuân theo FIFO; khi một file hoàn tất hoặc lỗi, file chờ tiếp theo tự động chạy mà không vượt quá giới hạn `N`.
- Có thao tác `Thử lại` cho riêng file lỗi sau khi mạng hoặc server phục hồi.
- Khi trùng tên, giao diện hỗ trợ lựa chọn `Ghi đè`, `Đổi tên` hoặc `Bỏ qua`.
- Lưu lịch sử gồm tên, dung lượng, thời gian và trạng thái; dữ liệu vẫn còn sau khi đóng/mở lại ứng dụng.
- Tìm kiếm lịch sử theo tên và lọc theo trạng thái thành công/lỗi.
- Regression bao phủ file thường, file lỗi, file trùng tên và hàng đợi hoạt động đồng thời.

### 1.5. Yêu cầu đã xác nhận trong dự án

Các nội dung sau được prompt hiện tại xác nhận, kể cả khi chi tiết ban đầu chỉ xuất hiện trong checklist:

- Có cả kéo-thả và nút chọn nhiều file.
- Bốn trạng thái cốt lõi là `Chờ`, `Đang tải`, `Hoàn tất`, `Lỗi`.
- Mỗi file có tiến trình và tốc độ riêng.
- Hàng đợi phải là FIFO và có giới hạn upload đồng thời `N`.
- Một file lỗi không làm dừng các file khác.
- Hệ thống phải hỗ trợ cả ba hành động trùng tên: `Ghi đè`, `Đổi tên`, `Bỏ qua`.
- Không triển khai Pause/Resume.
- Có lịch sử upload bền vững sau khi đóng/mở lại ứng dụng.
- Toàn bộ UI bằng tiếng Việt và hỗ trợ tên file Unicode.
- Python mục tiêu là 3.11 trở lên và GUI dùng PySide6.
- Transport chính là TCP.
- Metadata/lịch sử dùng MySQL 8.0+ khi được bật và JSON khi MySQL tắt.

Việc một khả năng đã được xác nhận không đồng nghĩa các tham số của nó đã được chốt. Ví dụ: FIFO đã xác nhận nhưng giá trị `N` chưa xác nhận; lịch sử bền vững đã xác nhận nhưng nơi lưu và mô hình đồng bộ chưa xác nhận.

### 1.6. Ngoài phạm vi hiện tại

- Pause/Resume upload.
- Xác thực người dùng, phân quyền, chia sẻ file và đồng bộ đám mây, trừ khi được bổ sung bằng yêu cầu mới.
- Mã hóa đầu cuối, chunked/resumable upload và triển khai production/Internet công cộng.
- Git push, cài dependency hoặc khởi chạy database trong giai đoạn lập kế hoạch này.

## 2. Kiến trúc dự kiến

### 2.1. Lựa chọn kỹ thuật đã xác nhận/đề xuất

- Runtime: Python 3.11+.
- GUI desktop: PySide6, do hỗ trợ drag-and-drop, signal/slot, progress bar và tác vụ nền tốt.
- Transport: TCP với control message JSON UTF-8 có length-prefix; giao thức truyền nội dung file sẽ được đặc tả riêng trước khi triển khai upload.
- Server: Python TCP server; scaffold dùng `socketserver.ThreadingTCPServer` cho health check, chưa có upload handler.
- Persistence: MySQL 8.0+ khi `MYSQL_ENABLED=true`; JSON history khi MySQL tắt.
- Test: pytest; integration test đi qua TCP protocol interface; GUI ưu tiên test state/queue/controller, còn thao tác kéo-thả có checklist thủ công hoặc pytest-qt nếu được duyệt.

Các dependency mới chỉ được khai báo trong `requirements.txt`, chưa được cài đặt.

### 2.2. Luồng xử lý chính

1. Người dùng kéo-thả hoặc chọn file.
2. Client chuẩn hóa đường dẫn, loại file trùng trong danh sách và chạy validation cục bộ.
3. File hợp lệ được tạo thành một upload item ở trạng thái `Chờ`.
4. Queue manager lấy item theo FIFO và chỉ cho tối đa `N` item ở trạng thái `Đang tải`.
5. Mỗi upload chạy độc lập; progress event cập nhật số byte đã gửi, phần trăm và tốc độ cho đúng item.
6. Server kiểm tra lại tên file, dung lượng, định dạng và chính sách trùng tên trước khi ghi file an toàn vào `uploads`.
7. Kết quả của từng file được ánh xạ vào bốn trạng thái cốt lõi; cách biểu diễn kết quả `Bỏ qua` vẫn cần xác nhận để không tự ý thêm trạng thái thứ năm.
8. Kết quả và metadata được ghi vào MySQL khi bật hoặc JSON khi MySQL tắt; GUI có thể tải lại lịch sử sau khi khởi động lại.
9. Dù một item hoàn tất hay lỗi, queue manager giải phóng slot và chạy item chờ kế tiếp.

### 2.3. Ranh giới module

- `client`: GUI, tương tác người dùng, state machine, queue, worker upload và API client.
- `server`: TCP handlers, validation phía server, lưu file, xử lý lỗi và điều phối nghiệp vụ upload.
- `shared`: model miền và hằng số dùng chung nhưng không chứa phụ thuộc GUI hoặc web framework.
- `protocol`: DTO/schema JSON, mã lỗi, tên field multipart và hợp đồng endpoint.
- `persistence`: repository và unit-of-work cho lịch sử/metadata; không để SQL rải trong GUI hoặc route.
- `database`: migration/seed MySQL và JSON history runtime trong chế độ fallback.
- `tests`: unit, integration và các test ánh xạ tới TC-01..TC-33.

### 2.4. Nguyên tắc thiết kế

- Một file là một đơn vị trạng thái và lỗi độc lập.
- Queue manager không phụ thuộc widget GUI để có thể unit test.
- Client validation phục vụ UX; server validation mới là hàng rào tin cậy cuối cùng.
- Tên file từ client không được dùng trực tiếp làm đường dẫn; server phải lấy basename, chặn path traversal và xử lý ghi file nguyên tử.
- Cấu hình `N`, dung lượng và định dạng dùng chung một nguồn cấu hình, nhưng server luôn tự kiểm tra lại.
- Response lỗi có mã máy đọc được và thông báo người dùng đọc được.
- Không ghi đè file hiện có nếu chưa có chính sách trùng tên rõ ràng và được người dùng chọn/xác nhận.

## 3. Cấu trúc thư mục đề xuất

> Cập nhật theo Prompt 2: cấu trúc có hiệu lực dùng `src/udm10` như cây mục tiêu trong `README.md`. Cây bên dưới là đề xuất lịch sử trước khi cấu trúc `src` được xác nhận và không còn dùng để tạo source mới.

```text
D:\UDM\
|-- client\
|   |-- __init__.py
|   |-- main.py
|   |-- controllers\
|   |   `-- upload_controller.py
|   |-- services\
|   |   |-- api_client.py
|   |   |-- queue_manager.py
|   |   `-- upload_worker.py
|   |-- state\
|   |   `-- upload_store.py
|   `-- ui\
|       |-- main_window.py
|       `-- widgets\
|           |-- drop_zone.py
|           `-- upload_item.py
|-- server\
|   |-- __init__.py
|   |-- main.py
|   |-- api\
|   |   `-- upload_routes.py
|   `-- services\
|       |-- file_storage.py
|       |-- upload_service.py
|       |-- validation.py
|       `-- conflict_resolver.py
|-- shared\
|   |-- __init__.py
|   |-- config.py
|   |-- errors.py
|   `-- models.py
|-- protocol\
|   |-- __init__.py
|   |-- constants.py
|   `-- schemas.py
|-- persistence\
|   |-- __init__.py
|   |-- connection.py
|   `-- upload_history_repository.py
|-- database\
|   |-- migrations\
|   |   `-- 001_create_upload_history.sql
|   |-- seeds\
|   |   `-- .gitkeep
|   `-- .gitkeep
|-- tests\
|   |-- unit\
|   |   |-- test_conflict_resolver.py
|   |   |-- test_queue_manager.py
|   |   |-- test_upload_state.py
|   |   `-- test_validation.py
|   |-- integration\
|   |   |-- test_upload_api.py
|   |   `-- test_upload_history.py
|   |-- e2e\
|   |   `-- manual-checklist.md
|   `-- conftest.py
|-- docs\
|   |-- implementation-plan.md
|   |-- architecture.md
|   |-- api-contract.md
|   `-- test-matrix.md
|-- uploads\
|   `-- .gitkeep
|-- .env.example
|-- .gitignore
|-- requirements.txt
`-- README.md
```

Cấu trúc gốc ở trên đã được thay thế có kiểm soát bởi cấu trúc `src/udm10` trong Prompt 2; không tạo thêm các package gốc `client`, `server`, `shared`, `protocol`, `persistence` để tránh trùng chức năng.

## 4. Danh sách module và trách nhiệm

| Module | Trách nhiệm | Ưu tiên |
|---|---|---|
| `domain.upload` | Upload item, trạng thái, metadata và kết quả; không phụ thuộc framework | P0 |
| `protocol.framing` | Length-prefix và JSON control message qua TCP | P0 |
| `protocol.upload_messages` | Hợp đồng message/file stream, mã lỗi và conflict policy | P0 |
| `client.controllers.queue_controller` | FIFO, giới hạn `N`, giải phóng slot khi xong/lỗi | P0 |
| `client.controllers.upload_controller` | Upload nền, progress event, tốc độ và cô lập lỗi | P0 |
| `client.models.upload_item` | State machine/presentation state độc lập từng file | P0 |
| `client.widgets.drop_zone` | Kéo-thả và chọn nhiều file | P0 |
| `client.ui.main_window` | Composition root cho GUI tiếng Việt | P0 |
| `server.tcp_server` | TCP lifecycle và dispatch control message | P0 |
| `server.upload_handler` | Nhận file stream, validation và kết quả có cấu trúc | P0 |
| `server.file_storage` | Ghi file an toàn và conflict resolver nguyên tử | P0/P1 |
| `persistence.history_repository` | Interface lưu/đọc/tìm kiếm lịch sử | P1 |
| `persistence.mysql_history` / `json_history` | Hai adapter MySQL và JSON tại persistence seam | P1 |
| `config.settings` | Cấu hình typed từ environment, không chứa secret | P0 |
| `tests` | Unit, integration, regression và truy vết checklist | P0-P2 |

## 5. Đối chiếu tên và vai trò TV1-TV6

Không hợp nhất hai nguồn thành một bảng phân công chính thức ở giai đoạn này. PDF là bảng **phân công kiểm thử**, còn DOCX là bảng **phân chia vai trò phát triển**; hai tài liệu có thể bổ trợ nhau nhưng không thể mặc nhiên xem là cùng một quyết định nhân sự.

### 5.1. Phiên bản trong PDF - Phân công kiểm thử

| Mã | Tên trong PDF | Phụ trách chính | Phối hợp |
|---|---|---|---|
| TV1 | Phạm Ngọc Phú | Kéo-thả, chọn file, validation UI; TC-01..TC-06 | TV6 |
| TV2 | Nguyễn Viết Thịnh | Trạng thái, tiến trình, tốc độ từng file; TC-07..TC-11 | TV1, TV6 |
| TV3 | Nguyễn Tấn Bão | API upload, lưu file, phản hồi server; TC-12..TC-14 | TV4, TV5 |
| TV4 | Phạm Trần Đức Phú | FIFO, giới hạn upload đồng thời; TC-15..TC-19 | TV3, TV6 |
| TV5 | Nguyễn Phi Long | Lỗi upload, mất mạng, trùng tên, retry; TC-20..TC-26 | TV3, TV6 |
| TV6 | Nguyễn Đăng Xuân Phát | Lịch sử upload, regression, UI danh sách lớn, bug list; TC-27..TC-33 | Tất cả |

### 5.2. Phiên bản trong DOCX - Phân chia vai trò phát triển

| Mã | Tên trong DOCX | Vai trò | Module/nhiệm vụ chính |
|---|---|---|---|
| TV1 | Phạm Ngọc Phú | Nhóm trưởng / Kiến trúc | Thiết kế tổng thể, API, project skeleton và GUI kéo-thả/danh sách file. |
| TV2 | Nguyễn Viết Thịnh | Dev Frontend - Trạng thái | State machine, progress bar, tốc độ và cập nhật UI thời gian thực. |
| TV3 | Nguyễn Tấn Bão | Dev Backend - Server | Endpoint multipart, lưu file và response trạng thái. |
| TV4 | Phạm Trần Đức Phú | Dev Backend - Hàng đợi | Queue và giới hạn `N`; DOCX gọi đây là module backend. |
| TV5 | Nguyễn Phi Long | Dev Backend - Lỗi/trùng tên | Conflict policy và cô lập lỗi. |
| TV6 | Nguyễn Đăng Xuân Phát | QA / Tổng hợp | Test, tích hợp, bug list, báo cáo, slide và demo. |

### 5.3. Khác biệt và điểm chưa thống nhất

- **Tên:** không phát hiện khác biệt; TV1..TV6 có cùng tên trong cả PDF và DOCX.
- **Bản chất phân công:** PDF giao quyền sở hữu nhóm test case; DOCX giao vai trò phát triển. Không suy ra người test cũng là người code module nếu chưa được nhóm xác nhận.
- **TV1:** PDF tập trung kéo-thả/chọn file/validation; DOCX bổ sung vai trò nhóm trưởng, kiến trúc và định nghĩa API.
- **TV4:** PDF chỉ xác định kiểm thử FIFO/concurrency; DOCX gọi module hàng đợi là backend. Kiến trúc đề xuất lại đặt queue điều phối upload ở client, nên cần chốt cả owner và layer.
- **TV6:** PDF giao kiểm thử lịch sử upload; DOCX giao QA/tổng hợp nhưng không chỉ định rõ người phát triển persistence/history.
- **TV2-TV3-TV5:** phạm vi hai nguồn tương đối đồng hướng, nhưng PDF vẫn là trách nhiệm kiểm thử còn DOCX là trách nhiệm phát triển.
- Chưa có phiên bản nhân sự chính thức được chọn. Cần nhóm xác nhận bảng phân công cuối cùng và người sở hữu module lịch sử.

Lưu ý phối hợp từ DOCX: TV3 cần chốt sớm hợp đồng API/progress; TV4 và TV5 phải tránh chồng chéo logic server; TV6 tham gia kiểm thử từ tuần đầu.

## 6. Lộ trình triển khai

### Giai đoạn 0 - Chốt yêu cầu và hợp đồng

- Xác nhận các mục ở phần 9.
- Chốt state machine, conflict policy và ranh giới client/server.
- Viết `docs/architecture.md`, `docs/api-contract.md` và ma trận TC-01..TC-33.
- Tiêu chí hoàn thành: không còn giá trị cấu hình quan trọng bị hard-code bằng giả định.

### Giai đoạn 1 - Project skeleton và vertical slice

- Tạo cấu trúc thư mục, cấu hình, logging và test harness.
- Làm luồng tối thiểu: chọn một file -> upload -> server lưu -> trả kết quả -> UI hoàn tất.
- Viết test API cho một file và request lỗi.
- Tiêu chí hoàn thành: một file hợp lệ chạy xuyên suốt client-server.

### Giai đoạn 2 - Nhiều file, state và hàng đợi

- Hoàn thiện drag-and-drop, danh sách item và state machine.
- Tách queue manager khỏi GUI; triển khai FIFO và giới hạn `N`.
- Thêm progress/tốc độ riêng cho từng file và test độc lập lỗi.
- Tiêu chí hoàn thành: TC lõi về nhiều file, tiến trình, FIFO và cô lập lỗi đạt.

### Giai đoạn 3 - Validation, lỗi, retry và trùng tên

- Validation đồng nhất client/server.
- Chuẩn hóa error code, xử lý mất mạng và retry riêng file lỗi.
- Triển khai conflict policy đã được xác nhận, kèm kiểm tra ghi file an toàn.
- Tiêu chí hoàn thành: TC-04, TC-05, TC-14 và TC-20..TC-26 đạt.

### Giai đoạn 4 - Persistence và lịch sử

- Tạo migration MySQL, JSON adapter và repository interface dùng chung.
- Lưu metadata, tải lại sau khởi động, tìm kiếm và lọc.
- Tiêu chí hoàn thành: TC-27..TC-30 đạt mà GUI không truy cập SQL trực tiếp.

### Giai đoạn 5 - Regression, UX và tài liệu

- Chạy ma trận TC-01..TC-33, trừ Pause/Resume được ghi rõ ngoài phạm vi.
- Kiểm tra tên Unicode/tên dài, danh sách lớn, file 0 byte, file lớn, N+1 và N+5.
- Sửa bug, chốt README, hướng dẫn chạy, báo cáo kiến trúc và demo script.
- Tiêu chí hoàn thành: không còn lỗi High; các lỗi Medium còn lại phải có quyết định chấp nhận rõ ràng.

## 7. Thứ tự ưu tiên

### P0 - Bắt buộc để đúng đề bài

- Kéo-thả hoặc chọn nhiều file, trạng thái độc lập và UI tiếng Việt/Unicode.
- Upload client-server, progress và tốc độ từng file.
- FIFO/giới hạn đồng thời, cô lập lỗi.
- Hỗ trợ đủ ba hành động trùng tên: ghi đè, đổi tên và bỏ qua.
- Lịch sử upload bền vững sau khi khởi động lại.
- Unit test queue/state và integration test upload.

### P1 - Mở rộng High trong checklist

- Validation định dạng/dung lượng/file rỗng.
- Retry và xử lý mất mạng.
- Request lỗi có response rõ ràng; test batch API theo hợp đồng được chốt.

### P2 - Hoàn thiện Medium

- Unicode/tên dài, UI danh sách lớn.
- Tìm kiếm/lọc lịch sử.
- Tối ưu UX, tài liệu demo và báo cáo.

## 8. Checklist hoàn thành

### Yêu cầu và thiết kế

- [ ] Các mục cần xác nhận đã có quyết định bằng văn bản.
- [ ] State machine và API contract không mâu thuẫn với TC-01..TC-33.
- [ ] Mỗi test case được ánh xạ tới test tự động hoặc bước test thủ công.

### Client

- [ ] Kéo-thả và chọn được một/nhiều file.
- [ ] Mỗi file có trạng thái, progress và tốc độ độc lập.
- [ ] GUI không treo khi upload; danh sách lớn cuộn và hiển thị đúng Unicode.
- [ ] FIFO và giới hạn `N` đúng cả khi thành công lẫn lỗi.
- [ ] Retry chỉ tác động file lỗi; không triển khai Pause/Resume ngoài phạm vi.

### Server

- [ ] API nhận multipart và trả response/mã lỗi ổn định.
- [ ] Validation phía server không tin dữ liệu phía client.
- [ ] Tên file được làm sạch; không path traversal.
- [x] Xử lý trùng tên theo lựa chọn rõ ràng và tránh race condition khi upload đồng thời.
- [ ] Lỗi một file không làm hỏng các file/request khác.

### Persistence

- [x] Migration MySQL tạo schema lặp lại được, không có thao tác phá hủy.
- [x] Lịch sử bền vững qua MySQL hoặc JSON và được tải lại khi client khởi động.
- [x] Tìm kiếm/lọc chạy trên model UI sau khi tải lịch sử bất đồng bộ.

### Kiểm thử và bàn giao

- [x] Unit/integration test state, queue, validation và conflict resolver (TC-20 đến TC-26).
- [x] Integration test TCP, filesystem storage và history (TC-27 đến TC-30).
- [ ] Regression checklist hoàn tất; TC-33 được ghi N/A đúng phạm vi.
- [ ] README mô tả setup, cấu hình, chạy client/server và test.
- [ ] Không commit database runtime, file upload thật, secret hoặc `.env`.

## 9. Cần xác nhận trước khi code

### Bắt buộc chốt

1. Giới hạn upload đồng thời `N`: kế hoạch nhân sự chỉ nêu ví dụ `3`, không phải giá trị đã xác nhận.
2. Dung lượng tối đa cho mỗi file và có giới hạn tổng của một lượt chọn/upload hay không.
3. Danh sách định dạng được phép: checklist dùng `.txt`, `.pdf`, `.jpg`, `.docx` làm dữ liệu hợp lệ nhưng chưa khẳng định đây là whitelist chính thức; cần chốt cả `.jpeg`, `.png` và chữ hoa/thường.
4. Đã xác nhận và triển khai: MySQL 8.0+ khi bật, JSON khi tắt; repository thuộc
   server, client đọc qua TCP. Schema gồm `upload_batches`, `upload_files`,
   `upload_events`. Chỉ retention/xóa lịch sử còn cần xác nhận.
5. Transport chính: **đã xác nhận là TCP**. Còn cần chốt wire protocol cho metadata/file bytes, giới hạn frame, checksum và cách client/server báo progress/kết quả.
6. Đã xác nhận không có chính sách trùng tên mặc định: server báo conflict và
   client chờ người dùng chọn `overwrite`, `rename` hoặc `skip`. Còn cần xác nhận
   có giữ tùy chọn áp dụng cùng lựa chọn cho các conflict đã phát hiện hay không.
7. File 0 byte được chấp nhận hay bị từ chối.
8. API nhận một file mỗi request hay nhiều file trong một request. Một file/request giúp progress và cô lập lỗi đơn giản hơn; checklist TC-13 có thể được hiểu là batch request.

### Cần chốt về sản phẩm/kỹ thuật

9. Mô hình concurrency cho TCP server: thread-per-connection, selector hay asyncio; scaffold đang dùng thread-per-connection chỉ cho health check.
10. Hệ điều hành mục tiêu có chỉ là Windows hay cần đa nền tảng.
11. Server chỉ chạy local/LAN hay phải hỗ trợ Internet; host, port và thư mục upload mặc định.
12. Khi người dùng chọn `Bỏ qua`, item dùng trạng thái mở rộng `Bỏ qua` hay ánh xạ vào một trong bốn trạng thái cốt lõi.
13. Retry có giới hạn số lần, backoff tự động hay chỉ chạy khi người dùng bấm `Thử lại`.
14. Đã xác nhận lịch sử ghi trạng thái thành công, lỗi và bỏ qua. Thời gian lưu
    và nhu cầu xóa lịch sử vẫn cần xác nhận.
15. Khi `Đổi tên`, quy tắc mong muốn là `name_1.ext`, timestamp hay UUID; xử lý đồng thời phải bảo đảm không trùng.
16. Progress yêu cầu chính xác theo byte gửi từ client hay server phải có endpoint/status event riêng; checklist nói tiến trình thật nhưng chưa định nghĩa giao thức.
17. Mức test GUI tự động mong muốn; có chấp nhận checklist thủ công cho drag-and-drop/hiển thị hay bắt buộc pytest-qt.
18. Bảng phân công nhân sự cuối cùng: phân biệt rõ người phát triển và người kiểm thử, xác nhận owner của history/persistence và queue nằm ở client hay server.

## 10. File sẽ tạo ở các bước tiếp theo

### Đã tạo trong bước lập kế hoạch

- `docs/implementation-plan.md`

### Chỉ tạo sau khi yêu cầu được xác nhận

- Tài liệu: `README.md`, `docs/architecture.md`, `docs/api-contract.md`, `docs/test-matrix.md`.
- Cấu hình: `.env.example`, `.gitignore`, `requirements.txt`.
- Source: các file trong `client`, `server`, `shared`, `protocol`, `persistence` như cây thư mục phần 3.
- Database/history: migration/seed MySQL trong `database`; JSON history runtime không đưa vào Git.
- Test: unit, integration và checklist E2E trong `tests`.
- Dữ liệu runtime: chỉ các file được upload trong `uploads`; không sao chép hoặc sửa tài liệu tham khảo.

## 11. Rủi ro và biện pháp giảm thiểu

| Rủi ro | Tác động | Biện pháp dự kiến |
|---|---|---|
| Chưa chốt `N`, dung lượng và định dạng | Test không ổn định, phải sửa validation/cấu hình | Chốt trước khi code; cấu hình hóa và kiểm tra ở cả client/server. |
| Wire protocol hoặc granularity thay đổi muộn | Phải viết lại worker, progress và integration test | TCP đã chốt; đặc tả metadata frame, file stream/chunk, checksum và kết quả trước vertical slice. |
| Upload chạy trên GUI thread | UI treo khi file lớn hoặc mất mạng | Worker nền, signal/slot và test responsiveness. |
| Progress/tốc độ không phản ánh byte gửi thật | Không đạt TC-10/TC-11 | Đo theo byte stream thực tế và thời gian đơn điệu; không mô phỏng progress. |
| Queue tồn tại ở cả client và server | Double scheduling, khó dự đoán FIFO và `N` | Chỉ định một nơi sở hữu concurrency; nơi còn lại chỉ bảo vệ tài nguyên. |
| Hai upload đồng thời trùng tên | Ghi đè/mất file ngoài ý muốn | Conflict resolver nguyên tử, lock hoặc tên tạm + atomic move. |
| File lớn được nạp toàn bộ vào RAM | Crash hoặc suy giảm hiệu năng | Streaming/chunked I/O nội bộ, giới hạn kích thước và test biên. |
| Tên Unicode, tên dài hoặc path traversal | Lỗi hiển thị, lỗi lưu file hoặc lỗ hổng bảo mật | Chuẩn hóa basename, giới hạn hợp lý, không tin đường dẫn client và test Unicode. |
| Lịch sử client/server không đồng nhất | UI hiển thị sai sau restart | Chọn một nguồn dữ liệu chính, migration rõ ràng và integration test restart. |
| Ý nghĩa trạng thái `Bỏ qua` chưa rõ | Mâu thuẫn với bốn trạng thái cốt lõi | Chốt mapping/status trước khi đóng API schema. |
| PDF và DOCX khác mục đích phân công | Bỏ sót owner hoặc giao chồng việc | Giữ hai bảng riêng và yêu cầu nhóm duyệt bảng phân công cuối cùng. |
| Checklist mở rộng bị hiểu thành yêu cầu bắt buộc | Scope creep | Duy trì truy vết: đề gốc / checklist / đã xác nhận / chưa xác nhận. |
