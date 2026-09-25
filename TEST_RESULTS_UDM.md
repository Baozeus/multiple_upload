# Kết quả kiểm thử UDM — TC_1 đến TC_12

## Môi trường

- Thời điểm: 2026-09-24 22:29 (Asia/Saigon)
- Windows 11, Python 3.12.14, PySide6
- Source: `D:\UDM\UDM_FIXED`
- Suite mới: **51/51 PASS**
- MySQL package/import/migration safety: **1/1 PASS**
- MySQL server thật: không chạy theo phạm vi an toàn
- TCP integration: localhost; không suy diễn thành LAN

## Kết quả chi tiết

| ID | Điều kiện | Kỳ vọng | Thực tế mới chạy | Kết quả | Bằng chứng |
|---|---|---|---|---|---|
| TC_1 | Một tệp `.txt` hợp lệ | Server lưu đúng dữ liệu, client nhận `SUCCESS` | Upload TCP thật và so byte nguồn/đích thành công | PASS | `test_tcp_upload_reports_progress_and_writes_file` |
| TC_2 | Kéo-thả hai tệp Unicode | Cả hai đi qua cùng luồng thêm file | `DropZone` phát đủ đường dẫn; cả hai xuất hiện trong queue | PASS | `test_drop_zone_emits_all_dropped_local_files`, ảnh UI |
| TC_3 | 6 tệp, mỗi tệp 128 KiB | 3 chạy, 3 chờ; cuối cùng 6 thành công | Health-check đo 3/3; hai đợt FIFO; SHA-256 của cả 6 cặp trùng | PASS | `test_tc3_tc10_six_real_uploads_run_in_fifo_waves_of_three` |
| TC_4 | 8 tệp hợp lệ trong một lần | Nhận 6 đầu, từ chối 2 cuối, không tạo worker cho 2 file dư | Queue chỉ có 6 item; đúng hai tên cuối trong rejected; batch sau có thể thêm lại; thông báo đúng câu yêu cầu | PASS | `test_rejected_overflow_never_enters_queue_and_can_be_added_next_time`, `test_eight_file_batch_reports_exact_six_accepted_two_rejected_message` |
| TC_5 | 512.000 byte và 512.001 byte | Mốc 500 KiB được áp dụng nhất quán | 512.000 được chấp nhận; 512.001 bị từ chối; config không thể nâng trần | PASS | `test_accepts_supported_extension_at_exact_500_kib_limit`, `test_rejects_file_larger_than_500_kib`, `test_config_cannot_raise_confirmed_500_kib_limit` |
| TC_6 | Tệp trùng tên | Rename/overwrite/skip đúng chính sách | TCP thật kiểm tra cả ba nhánh; file cũ được bảo toàn khi cần | PASS | `test_tcp_rename_overwrite_and_skip`, `test_tcp_ask_reports_duplicate_without_sending_payload` |
| TC_7 | Định dạng ngoài whitelist | Không vào queue/server | `.zip`/đuôi không hỗ trợ bị từ chối | PASS | `test_fifo_limit_and_validation`, `test_rejects_unsupported_extension` |
| TC_8 | Server offline rồi bật lại | File lỗi có thể thử lại; file khác không bị kẹt | Lần đầu `ERROR`, khởi động server cùng port rồi retry thành công; SHA-256 trùng | PASS | `test_tc8_offline_file_can_be_retried_after_server_starts`, health/storage tests |
| TC_9 | Tệp 500 KiB, ACK trễ | Progress byte-based không giảm; tốc độ hữu hạn; chưa hoàn tất trước ACK | Có nhiều mốc trung gian; dùng monotonic; giữ 99% và “Đang chờ Server xác nhận”; chỉ 100% sau `SUCCESS` | PASS | `test_progress_is_monotonic_and_waits_for_server_ack_before_success`, `test_payload_sent_stays_uploading_until_server_ack` |
| TC_10 | 6 tệp với server test đọc chậm; thêm client thứ tư; một tệp lỗi | Đạt 3 nhưng không vượt 3; đợt sau chạy; lỗi giải phóng slot | Đo 3/3 qua health-check; client ngoài bị `REJECTED`; file kế tiếp sau lỗi hoàn tất; không `.part` | PASS | Hai test `test_tc3_tc10_*`, `test_tc10_failed_upload_releases_slot_and_next_file_completes` |
| TC_11 | Persistence MySQL | Lịch sử ghi/đọc trên MySQL test | Người dùng từng ghi nhận PASS; lần này chỉ package/import/migration safety PASS, không kết nối MySQL thật | NOT RUN (integration) | `evidence/mysql-package-tests.log`; cần MySQL test riêng để xác minh DB thật |
| TC_12 | Server localhost trên port ngẫu nhiên khác 9000; endpoint sai | Health/upload dùng đúng endpoint; endpoint sai báo lỗi | Health `ready`, upload + SHA-256 thành công ở port khác 9000; port đóng báo lỗi; UI khóa endpoint khi queue chạy | PASS | `test_tc12_alternate_port_health_upload_and_wrong_endpoint`, `test_endpoint_fields_are_locked_until_waiting_and_uploading_items_finish` |

## Phân biệt kết quả cũ và kết quả mới

Các ghi nhận PASS cũ của người dùng cho TC_1, TC_2, TC_5, TC_6, TC_7, TC_8, TC_11 chỉ là ngữ cảnh. Bảng trên dùng kết quả chạy mới. Riêng TC_11 không được nâng thành PASS integration vì lần chạy này không có MySQL test server.

## Phân lớp test

- Logic/config/queue: `test_config_and_queue.py`, `test_protocol_and_storage.py`.
- TCP thật: `test_tcp_smoke.py`, `test_health_check.py`, `test_target_tcp_integration.py`.
- GUI/headless: `test_connection_coordinator.py`, `test_ui_connection_controls.py`.
- Kiểm tra trực quan Windows: `evidence/gui-1120x700.png`, `gui-1366x768.png`, `gui-1920x1080.png`, `gui-duplicate-dialog.png`.

## Phần chưa chạy

- MySQL integration thật: NOT RUN — không có/không được phép dùng database test trong nhiệm vụ này.
- LAN giữa hai máy: NOT RUN — chỉ xác minh localhost.
- Pause/Resume: N/A — ngoài phạm vi.
