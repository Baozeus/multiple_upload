# Gói bàn giao giao diện Multiple Upload (UDM_10)

## Mục đích

`Code/ui-handoff/` chứa client desktop PySide6 và các module
nội bộ tối thiểu để giao diện có thể import, khởi chạy và hiển thị đầy đủ các
trạng thái upload. Gói này không sửa source gốc, không chứa server, database,
dữ liệu lịch sử, thông tin đăng nhập hay cấu hình máy cá nhân.

Giao diện hiện có hai khu vực: **Tải lên** và **Tệp đã tải**. Hàng đợi hỗ trợ
tối đa 6 lượt upload đồng thời; các file còn lại ở trạng thái `Chờ`.

## Cây thư mục

```text
Code/ui-handoff/
├── README.md
├── MANIFEST.md
└── client/
    ├── config.example.json
    ├── requirements.txt
    ├── run.py
    └── multiple_upload_client/
        ├── __init__.py
        ├── __main__.py
        ├── config.py
        ├── history.py
        ├── main_window.py
        ├── models.py
        ├── queue_manager.py
        ├── theme.py
        ├── uploader.py
        └── widgets.py
```

Không có thư mục asset riêng: logo và icon của UI được vẽ trực tiếp bằng
`QPainter`/`QPainterPath` trong `widgets.py`, do đó không cần tải ảnh ngoài.

## File được bao gồm

| File/nhóm file | Vai trò |
|---|---|
| `client/run.py`, `multiple_upload_client/__main__.py` | Điểm khởi chạy độc lập của client. |
| `main_window.py` | Layout, điều hướng, trang upload, trang lịch sử và hộp thoại xử lý tên trùng. |
| `widgets.py` | Component UI, logo/icon vector, drop zone, dòng file, badge trạng thái và dòng lịch sử. |
| `theme.py` | Design tokens và Qt stylesheet dùng chung. |
| `models.py` | Mô hình dữ liệu mà component UI đọc để hiển thị trạng thái và tiến trình. |
| `queue_manager.py` | Hàng đợi tối đa 6 file đồng thời; cần để UI hoạt động độc lập. |
| `uploader.py` | Coordinator, signal và adapter upload/mock mà `MainWindow` sử dụng trực tiếp. |
| `history.py` | Kiểu dữ liệu và store lịch sử mà trang **Tệp đã tải** sử dụng. |
| `config.py` | Đọc URL/endpoint từ config hoặc biến môi trường; không chứa địa chỉ thật. |
| `requirements.txt` | Dependency UI duy nhất: PySide6. |
| `config.example.json` | Cấu hình mẫu đã làm sạch, không có URL máy cá nhân hay secret. |

`models.py`, `queue_manager.py`, `uploader.py`, `history.py` và `config.py` vừa
hỗ trợ UI vừa chứa logic runtime tối thiểu. Chúng được giữ vì bỏ đi sẽ làm
client không thể import hoặc không thể thể hiện hàng đợi/progress/lịch sử.
**Cần nhóm xác nhận** cách merge nếu nhánh tổng hợp đã có implementation tương
đương; không nên ghi đè mù quáng các module đó.

## File cố ý không bao gồm

Đã loại 19 file source/tài liệu nhìn thấy trong project khỏi gói bàn giao:

- Toàn bộ `server/`: Flask backend, template web, CSS/JavaScript web, test và
  dependency server; không thuộc client desktop.
- `client/tests/`: test và script render phục vụ phát triển, không phải runtime UI.
- `client/config.json`: chứa URL theo máy hiện tại; thay bằng
  `config.example.json` đã làm sạch.
- `client/README.md`, `README.md`, `PRODUCT.md`, `DESIGN.md` và
  `docs/web-ui-design.md`: tài liệu nguồn không cần để import/chạy UI; nội dung
  tích hợp cần thiết đã được cô đọng trong README này.
- Không sao chép `.env`, credential, database, file lịch sử thật, `.git`,
  `.venv`, `__pycache__`, cache, log, build output hay file tạm. Các thư mục
  sinh tự động này không nằm trong con số 19 ở trên.

## Dependency UI

- Python 3.11 trở lên được khuyến nghị.
- `PySide6==6.9.1` theo `client/requirements.txt`.
- Không có package ảnh/icon bên ngoài và không có asset runtime rời.

## Cách áp dụng vào nhánh tổng hợp

1. Tạo nhánh tích hợp riêng và đảm bảo working tree sạch.
2. Sử dụng `Code/ui-handoff/client/multiple_upload_client/` làm package client của
   dự án tổng hợp, giữ nguyên package name `multiple_upload_client`.
3. Chạy `Code/ui-handoff/client/run.py` làm entry point; nếu nhánh đích đã có entry point tương
   đương. Nếu đã có, giữ entry point cũ và gọi
   `multiple_upload_client.__main__.main()`.
4. Gộp dependency `PySide6==6.9.1` vào dependency/lock file của nhánh đích;
   không xóa các dependency đang có.
5. Chỉ khi cần cấu hình bằng file, sao chép `config.example.json` thành
   `config.json`, rồi điền URL phù hợp. Không commit secret hoặc URL cá nhân.
6. Nếu nhánh đích đã có uploader/hàng đợi/lịch sử, ưu tiên giữ implementation
   nghiệp vụ và tạo adapter đáp ứng các interface ở mục tiếp theo; tránh ghi đè
   logic đã được nhóm tổng hợp kiểm thử.
7. Chạy kiểm tra import và smoke test trước khi merge.

## Interface cần giữ tương thích

- `ClientConfig`: các thuộc tính `base_url`, `upload_endpoint`, `upload_url`,
  `allow_mock_fallback`; đọc được các biến môi trường
  `UDM10_API_BASE_URL`, `UDM10_UPLOAD_ENDPOINT`,
  `UDM10_ALLOW_MOCK_FALLBACK` và `UDM10_HISTORY_FILE`.
- `UploadCoordinator`: các signal `item_added`, `item_updated`, `item_removed`,
  `duplicate_found`, `queue_changed`, `mode_changed`, `notification`,
  `item_terminal`; các hàm `add_files`, `get_item`, `remove_item`,
  `clear_removable`, `retry`, `request_conflict_resolution`,
  `resolve_conflict`.
- `UploadItem`/`UploadStatus`: phải cung cấp tên, đường dẫn, dung lượng, phần
  mở rộng, status, progress, speed, detail, conflict state và elapsed time như
  component hiện tại sử dụng.
- `HistoryStore`: `list_records()` và `upsert(...)`; `HistoryRecord` cung cấp
  dữ liệu tên, loại, dung lượng, thời điểm, trạng thái và kết quả xử lý trùng.
- API upload hiện được kỳ vọng là
  `POST {base_url}{upload_endpoint}`, multipart field `file`; HTTP `409` mở hộp
  thoại `Ghi đè` / `Đổi tên` / `Bỏ qua`. Hai lựa chọn đầu dùng query
  `conflict=overwrite|rename`. **Cần xác nhận** contract chính thức với backend.
- Badge trạng thái API không hiển thị trên UI, nhưng logic cấu hình/kết nối bên
  dưới vẫn được giữ nguyên.

Server hiện chưa có API lịch sử trong source được phân tích. Client lưu kết quả
cục bộ tại `%LOCALAPPDATA%\UDM_10\upload_history.json` (hoặc đường dẫn từ
`UDM10_HISTORY_FILE`). Lịch sử này không đồng bộ giữa các máy.

## Chạy giao diện từ gói

Các lệnh PowerShell sau giả định dependency đã được cài trong virtual
environment của nhóm:

```powershell
cd Code\ui-handoff\client
python run.py
```

Nếu cần tạo môi trường mới, nhóm có thể dùng dependency đã khai báo:

```powershell
cd Code\ui-handoff\client
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py
```

`config.json` là tùy chọn. Khi không cấu hình `base_url`, UI vẫn khởi chạy và
dùng mock fallback để kiểm tra trạng thái giao diện.

## Lệnh kiểm tra sau khi áp dụng

```powershell
cd Code\ui-handoff\client
python -m compileall multiple_upload_client
python -c "from multiple_upload_client.main_window import MainWindow; print('UI import OK')"
python run.py
```

Kiểm tra thủ công tối thiểu: cửa sổ 1366×768 và 1920×1080, danh sách trống,
kéo-thả, chọn trên 6 file, tiến trình độc lập, lỗi một file, xử lý tên trùng và
trang lịch sử.

## Cần nhóm xác nhận

- Endpoint, multipart field và schema response chính thức của API upload.
- Contract xử lý `overwrite`/`rename` và quy tắc đặt tên mới.
- API lịch sử upload để thay thế local store khi backend hỗ trợ.
- Giới hạn dung lượng và định dạng file.
- Cách hợp nhất các module runtime hỗn hợp nếu nhánh tổng hợp đã có logic riêng.
