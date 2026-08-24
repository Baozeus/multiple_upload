# UI Wireframe - UDM_10 Desktop

## 1. Quy ước

- Wireframe mô tả hierarchy, topology và hành vi; không phải pixel-perfect comp.
- `●` online/success, `◷` waiting, `↑` uploading, `!` error/conflict, `○` neutral/offline.
- Màu không được suy ra từ ký hiệu; implementation phải dùng icon + nhãn chữ.

## 2. Upload workspace - 1366x768

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  ↑  UDM_10       [ Tải tệp ]   Lịch sử                                                    ● Đã kết nối   127.0.0.1:9000 │ 56
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                                              │
│  ┌──────────────────────────────┐  ┌──────────────────────────────────────────────────────────────────────────────────────┐  │
│  │  ↑                           │  │                                  ↑                                                   │  │
│  │  Multiple Upload             │  │                     Kéo và thả tệp vào đây                                            │  │
│  │  Tải nhiều tệp lên máy chủ   │  │                   hoặc  [ Chọn tệp ]                                                  │  │
│  │  nhanh chóng và an toàn      │  │              Giới hạn sẽ hiển thị sau khi được xác nhận                              │  │
│  └──────────────────────────────┘  └──────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                                              │
│  Tổng số tệp          Đang tải            Đang chờ             Thành công             Lỗi                                   │
│  6                    ↑ 2                  ◷ 2                   ✓ 1                     ! 1                                    │
│  ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────  │
│                                                                                                                              │
│  Hàng đợi tải lên                                                                                                            │
│  ┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ TỆP                              DUNG LƯỢNG   TRẠNG THÁI      TIẾN TRÌNH                 TỐC ĐỘ       HÀNH ĐỘNG          │  │
│  ├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤  │
│  │ [PDF] Bao-cao-thang-08.pdf        12,4 MB      ↑ Đang tải      ███████████░░  76%          4,2 MB/s     —                  │  │
│  │ [JPG] anh-su-kien.jpg              6,8 MB      ↑ Đang tải      ███████░░░░░░  48%          2,1 MB/s     —                  │  │
│  │ [DOC] hop-dong.docx                1,3 MB      ◷ Đang chờ      ─────────────  Thứ 1        —            [ Xóa ]             │  │
│  │ [ZIP] tai-lieu.zip                84,1 MB      ! Lỗi           ─────────────  —            —            [Thử lại] [Xóa]     │  │
│  │      Không thể kết nối tới máy chủ. Kiểm tra kết nối rồi thử lại.                                                       │  │
│  └────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Vertical budget

- Navigation: 56px.
- Workspace padding top/bottom: 24px.
- Header + drop band: khoảng 144px.
- Summary: 56px.
- Queue heading/table header: khoảng 72px.
- Upload row: tối thiểu 64px; queue viewport cuộn độc lập khi vượt phần còn lại.

## 3. Empty state

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  Multiple Upload                                                                                      │
│  Tải nhiều tệp lên máy chủ nhanh chóng và an toàn                                                     │
│                                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                             ↑                                                  │  │
│  │                                Kéo và thả tệp vào đây                                          │  │
│  │                                      [ Chọn tệp ]                                              │  │
│  │                   Có thể chọn nhiều tệp • [định dạng] • tối đa [dung lượng]                     │  │
│  └────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                      │
│  Tổng số tệp 0      Đang tải 0      Đang chờ 0      Thành công 0      Lỗi 0                           │
│                                                                                                      │
│                                     Chưa có tệp trong hàng đợi                                       │
│                       Các tệp bạn thêm sẽ xuất hiện ở đây với trạng thái riêng.                       │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 4. Drag-over

```text
┌══════════════════════════════════════════════════════════════════════════════════════════════════════┐
║                                             ↓                                                        ║
║                               Thả tệp để thêm vào hàng đợi                                           ║
║                           Tệp sẽ được kiểm tra trước khi tải lên                                      ║
└══════════════════════════════════════════════════════════════════════════════════════════════════════┘
```

- Dùng accent border 2px và `accent-subtle`; không nhấp nháy.
- Khi con trỏ rời vùng hợp lệ, trở lại state trước đó trong 160ms.

## 5. Duplicate conflict - inline expansion

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [PDF] Bao-cao.pdf       2,8 MB       ! Cần xử lý        File đã tồn tại trên máy chủ                  │
├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  ! Máy chủ đã có tệp “Bao-cao.pdf”. Bạn muốn xử lý thế nào?                                          │
│                                                                                                      │
│  ( ) Ghi đè     Thay thế tệp hiện có bằng tệp mới.                                                    │
│  ( ) Đổi tên    Giữ cả hai; tên mới sẽ được máy chủ tạo an toàn.                                     │
│  ( ) Bỏ qua     Không tải tệp này lên.                                                               │
│                                                                                                      │
│  [ ] Áp dụng cho các tệp trùng còn lại                          [ Xóa khỏi hàng đợi ] [ Tiếp tục ]    │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Không chọn sẵn radio cho đến khi policy mặc định được xác nhận.

## 6. Server offline

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ○ Mất kết nối server   Không thể bắt đầu tệp mới. Các tệp đang chờ vẫn được giữ lại.   [Thử kết nối] │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

- Banner nằm dưới navigation, phía trên workspace.
- Không dùng modal chặn thao tác.
- File đang upload chuyển `Lỗi` với nguyên nhân cụ thể; các file chưa bắt đầu giữ `Đang chờ`.
- Việc tự chạy lại khi kết nối phục hồi còn chờ xác nhận.

## 7. History workspace

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  ↑  UDM_10         Tải tệp   [ Lịch sử ]                                                   ● Đã kết nối   127.0.0.1:9000 │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                                              │
│  Lịch sử upload                                                                                                              │
│  Xem lại kết quả các tệp đã xử lý.                                                                                           │
│                                                                                                                              │
│  [ 🔍 Tìm theo tên tệp...                                            ]   Trạng thái [ Tất cả         ▾ ]                    │
│                                                                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ TÊN TỆP                                      THỜI GIAN                 DUNG LƯỢNG             KẾT QUẢ                 │  │
│  ├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤  │
│  │ Bao-cao-thang-08.pdf                          23/08/2026 21:42          12,4 MB                 ✓ Thành công            │  │
│  │ hop-dong.docx                                 23/08/2026 21:39           1,3 MB                 ✓ Đã đổi tên            │  │
│  │ tai-lieu.zip                                  23/08/2026 21:31          84,1 MB                 ! Lỗi                   │  │
│  └────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 8. History empty/loading/no-results

### Loading

```text
[ Search disabled skeleton                         ] [ Filter skeleton ]
────────────────────────────────────────────────────────────────────────
██████████████████        ███████████       ███████       █████████
██████████████            ███████████       ███████       █████████
████████████████████      ███████████       ███████       █████████
```

### Empty history

```text
                                ◷
                       Chưa có lịch sử upload
             Khi một tệp được xử lý, kết quả sẽ xuất hiện ở đây.
                              [ Tải tệp ]
```

### No search results

```text
                                ⌕
                     Không tìm thấy tệp phù hợp
          Thử từ khóa khác hoặc bỏ bộ lọc trạng thái hiện tại.
                         [ Xóa tìm kiếm và bộ lọc ]
```

## 9. Keyboard map

1. Navigation `Tải tệp`.
2. Navigation `Lịch sử`.
3. Connection action nếu offline.
4. Drop zone / `Chọn tệp` (một tab stop ưu tiên; tránh hai control cùng hành vi).
5. Queue actions theo thứ tự row từ trên xuống.
6. Search, clear-search, status filter trong History.
7. History row actions nếu sau này được xác nhận.

Focus ring 2px phải luôn nhìn thấy, kể cả trên drag-over hoặc error background.
