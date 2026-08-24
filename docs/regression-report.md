# Regression report

## Kết quả sau sửa

| Tầng | Lệnh | Kết quả |
|---|---|---|
| Unit | `python -m pytest tests\unit -q --disable-warnings` | 20 pass + 12 subtests |
| Integration | `python -m pytest tests\integration -q --disable-warnings` | 25 pass |
| UI | `python -m pytest tests\ui -q --disable-warnings` | 20 pass |
| Import/bytecode | `python -m compileall -q src run_client.py run_server.py` | Pass |

Tổng: **65 test + 12 subtests pass**. Không có failure. TC-33 được đánh dấu N/A
ở ma trận yêu cầu.

## Phạm vi regression

- `.txt`, `.pdf`, `.jpg`, `.docx`; sai định dạng; 0 byte; file lớn.
- N, N+1, N+5; FIFO; fail giải phóng slot; progress/tốc độ độc lập.
- TCP một/nhiều file, Unicode, payload thiếu, timeout/disconnect, path traversal.
- Duplicate conflict, overwrite/rename/skip, concurrent reservation, manual retry.
- JSON/MySQL selection, fail-fast, metadata/events, history search/filter/error.
- UI empty/drag-over/offline/loading/no-results, 10 trạng thái hỗn hợp, 100 dòng,
  tên dài/Unicode, dialog và keyboard action.
- Visual confirmation ở 1366×768, 1920×1080 và minimum 960×640.

## Kết luận

BUG-001 không tái diễn. Không phát hiện regression chức năng hoặc bố cục. Không
thay đổi yêu cầu để làm test pass.
