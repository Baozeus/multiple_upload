# Báo cáo kiểm thử UDM_10

Ngày chạy: 2026-08-24. Môi trường: Windows, Python 3.11+, PySide6 offscreen cho
automation UI; visual QA bằng screenshot deterministic. Owner lấy đúng từ PDF,
không được hiểu là xác nhận đóng góp thực tế.

## Tổng hợp

- TC-01..TC-32: **PASS**.
- TC-33 Pause/Resume: **N/A**, ngoài phạm vi đã chốt.
- Automation: **65 test + 12 subtests pass**.
- Visual QA: 1366×768, 1920×1080, 960×640 và 14 state pass.
- Bug: 1 Low đã sửa, 0 bug mở.

## Ma trận checklist

| ID | Người phụ trách | Kết quả | Bằng chứng | Ghi chú |
|---|---|---|---|---|
| TC-01 | TV1 | PASS | `test_drop_zone_accepts_real_local_file_urls` | Drag/drop file thật, signal nhận Path. |
| TC-02 | TV1 | PASS | Drop pipeline + multi-file picker test | Cùng pipeline hỗ trợ list nhiều file. |
| TC-03 | TV1 | PASS | `test_tc03_file_picker_emits_every_selected_file` | Picker trả đủ txt/pdf/jpg/docx, không mất/trùng. |
| TC-04 | TV1 | PASS | `test_tc04_*` trong `test_upload_validation.py` | Invalid bị từ chối trước payload; whitelist thật cần xác nhận. |
| TC-05 | TV1 | PASS | `test_tc05_file_over_configured_limit_is_rejected` | Limit hoạt động khi cấu hình; giá trị thật cần xác nhận. |
| TC-06 | TV1 | PASS | Long Unicode accessibility + TCP Unicode tests | Tên đầy đủ giữ trong tooltip/accessibility. |
| TC-07 | TV2 | PASS | Queue/unit và mixed UI screenshot | File mới waiting, slot rảnh chuyển uploading. |
| TC-08 | TV2 | PASS | TCP client/server integration | Kết thúc completed, 100%. |
| TC-09 | TV2 | PASS | Provider network failure/UI failed tests | Chỉ item liên quan fail, có thông báo. |
| TC-10 | TV2 | PASS | `test_tc10_large_file_is_streamed_in_chunks_with_monotonic_progress` | ~5 MiB, >32 progress update, stream theo chunk. |
| TC-11 | TV2 | PASS | `test_progress_and_speed_are_independent_per_upload` | %/speed từng item độc lập. |
| TC-12 | TV3 | PASS | `test_uploads_one_binary_file_over_tcp` | Lưu đúng binary, result riêng. |
| TC-13 | TV3 | PASS | Multiple Unicode files + provider E2E | Nhiều file có result/request ID riêng. |
| TC-14 | TV3 | PASS | Missing payload, unsafe name, next-file tests | Error rõ, server không crash. |
| TC-15 | TV4 | PASS | Queue `max_concurrent=3` tests | Không quá N uploading. |
| TC-16 | TV4 | PASS | `test_n_plus_one_keeps_only_n_uploading_in_fifo_order` | N+1 ở waiting. |
| TC-17 | TV4 | PASS | `test_terminal_result_releases_slot_for_next_fifo_item` | Hoàn tất giải phóng slot. |
| TC-18 | TV4 | PASS | `test_tc18_n_plus_five_preserves_fifo_for_every_waiting_file` | Thứ tự bắt đầu đúng enqueue. |
| TC-19 | TV4 | PASS | `test_tc19_failed_slot_starts_next_waiting_file` | File lỗi vẫn mở slot cho file kế. |
| TC-20 | TV5 | PASS | `test_tc20_network_failure_only_fails_related_file_and_queue_continues` | Các file khác tiếp tục. |
| TC-21 | TV5 | PASS | Disconnect/client conflict/offline tests | Item liên quan báo lỗi; app không treo. |
| TC-22 | TV5 | PASS | `test_tc22_retry_is_manual_and_replaces_attempt_history` | Retry thủ công chỉ item lỗi. |
| TC-23 | TV5 | PASS | Conflict server + dialog tests | Không policy mặc định; dialog tự mở. |
| TC-24 | TV5 | PASS | Overwrite exact-target test | Overwrite đúng target, atomic. |
| TC-25 | TV5 | PASS | Rename preserves-original test | Giữ file cũ, tên mới duy nhất. |
| TC-26 | TV5 | PASS | Skip + concurrent reservation tests | Không payload, trạng thái/thông báo rõ. |
| TC-27 | TV6 | PASS | JSON full metadata + TCP persistence | Tên, size, time, status, batch được lưu. |
| TC-28 | TV6 | PASS | Repository restart/MySQL fail-fast tests | JSON còn sau restart; MySQL lỗi thì dừng. |
| TC-29 | TV6 | PASS | History proxy search test | Tìm theo tên Unicode. |
| TC-30 | TV6 | PASS | Search/filter + async load/error test | Lọc đúng, GUI không chặn. |
| TC-31 | TV6 | PASS | Full unit/integration/UI regression | Luồng thường/lỗi/trùng/queue cùng hoạt động. |
| TC-32 | TV6 | PASS | 10-row screenshots + 100-row UI test | Scroll, ellipsis/tooltip, keyboard hoạt động. |
| TC-33 | TV6 | N/A | Phạm vi dự án | Không triển khai/kiểm thử Pause/Resume. |

## Bằng chứng trực quan

Ảnh QA cục bộ ở `.impeccable/review/prompt10-final/` gồm upload mixed/empty,
drag-over, offline/reconnecting, duplicate dialog và history
populated/empty/loading/no-results/error. Thư mục này được ignore và không push.

## Điểm cần xác nhận

- Giá trị production của `MAX_FILE_SIZE_MB`.
- Danh sách production của `ALLOWED_EXTENSIONS`.
- Danh tính/vai trò TV1–TV6 do PDF và DOCX không đồng nhất.
