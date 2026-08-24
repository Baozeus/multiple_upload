# UI States and Behaviors - UDM_10

## 1. Nguyên tắc state

- Bốn trạng thái upload bền vững vẫn là `Chờ`, `Đang tải`, `Hoàn tất`, `Lỗi`.
- `Drag-over`, `Duplicate conflict`, `Server offline` và các state History là UI/transient state, không tự ý thay đổi domain enum.
- Mỗi state phải có icon, nhãn chữ và màu; màu không đứng một mình.
- Một thay đổi chỉ cập nhật row liên quan và summary tương ứng; không redraw toàn danh sách nếu không cần.
- Copy lỗi gồm hai phần: điều đã xảy ra và hành động tiếp theo.

## 2. Upload state matrix

| State | Trigger | Hiển thị | Hành động | Chuyển tiếp |
|---|---|---|---|---|
| Empty | Queue không có item | Drop zone mở rộng; summary đều 0; empty message dạy thao tác | `Chọn tệp`, drag-drop | File hợp lệ -> Waiting; file bị từ chối -> validation feedback |
| Drag-over | Con trỏ mang file nằm trong drop zone | Accent border 2px, icon mũi tên xuống, copy `Thả tệp để thêm vào hàng đợi` | Thả file hoặc rời vùng | Drop -> validation; leave -> state trước đó |
| Waiting | File hợp lệ nhưng chưa có slot | Icon đồng hồ, `Đang chờ`, vị trí FIFO nếu biết; chưa có progress màu | `Xóa` | Có slot -> Uploading; xóa -> remove row |
| Uploading | Worker đang gửi bytes | Icon upload, `Đang tải`, progress determinate, %, tốc độ | Không Pause/Resume; không Xóa mặc định | Thành công -> Completed; transport/storage error -> Failed; conflict -> Duplicate conflict |
| Completed | Server xác nhận lưu thành công | Check icon, `Hoàn tất`, progress 100%, thời gian hoàn tất | `Xóa` khỏi queue nếu được duyệt | Ghi history; remove chỉ ảnh hưởng current queue |
| Failed | File-specific error | Error icon, `Lỗi`, error detail 1-2 dòng | `Thử lại`, `Xóa` | Retry -> Waiting; remove -> remove row |
| Duplicate conflict | Server báo tên đã tồn tại | Warning icon, `Cần xử lý`, DuplicateDialog modal | `Ghi đè`, `Đổi tên`, `Bỏ qua`, `Tiếp tục` | Overwrite/rename -> Waiting rồi nhận slot; skip -> Skipped, không gửi payload |

## 3. Detailed behaviors

### 3.1. Empty state

- Focus mặc định không tự nhảy; tab đầu tiên tới navigation, sau đó drop zone.
- Drop zone có accessible name: `Chọn hoặc thả nhiều tệp để tải lên`.
- Không hiển thị giới hạn giả; dùng helper text tổng quát hoặc placeholder trong bản thiết kế cho tới khi `N`, size và extensions được chốt.

### 3.2. Drag-over

- Chỉ active khi payload chứa file path hợp lệ; payload text thường không kích hoạt.
- Không đổi layout hoặc làm nội dung nhảy.
- Nếu một phần file hợp lệ và một phần không hợp lệ, sau drop hiển thị kết quả validation theo từng file, không từ chối im lặng cả lô.

### 3.3. Waiting

- Row hiển thị `Đang chờ`; có thể thêm `Thứ n trong hàng đợi` nếu queue cung cấp ổn định.
- Xóa item chờ phải cập nhật vị trí các item phía sau nhưng không thay đổi thứ tự tương đối.
- Khi server offline, item vẫn Waiting thay vì Failed nếu chưa bắt đầu truyền.

### 3.4. Uploading

- Progress bar dùng determinate khi biết tổng bytes; text phần trăm luôn hiện.
- Tốc độ được làm mượt trong cửa sổ thời gian ngắn để tránh nhảy số liên tục nhưng không giả lập.
- Không thêm Pause/Resume.
- Nếu mất kết nối, chỉ row bị ảnh hưởng chuyển Failed; slot được giải phóng theo quy tắc queue đã xác nhận.

### 3.5. Completed

- Confirmation không dùng toast làm tín hiệu duy nhất; row giữ trạng thái đọc được.
- Summary `Thành công` tăng và history được cập nhật sau xác nhận server/persistence.
- Nếu history write thất bại nhưng upload thành công, không được đổi upload thành Failed; cần lỗi persistence riêng trong telemetry/log và UX phù hợp ở bước sau.

### 3.6. Failed

- Message mẫu network: `Không thể kết nối tới máy chủ. Kiểm tra kết nối rồi thử lại.`
- Message mẫu validation: `Tệp vượt quá dung lượng cho phép. Chọn tệp nhỏ hơn [giới hạn].`
- Message mẫu server: `Máy chủ không thể lưu tệp. Thử lại hoặc liên hệ người quản trị.`
- `Thử lại` chỉ retry file đó; không reset progress/trạng thái của file khác.
- Khi retry, progress về 0 và row trở lại Waiting trước khi nhận slot.

### 3.7. Duplicate conflict

- Decision tray xuất hiện ngay dưới row, không dùng modal mặc định.
- Focus/announcement đi tới heading `Tệp đã tồn tại trên máy chủ`, nhưng không làm mất keyboard context của danh sách.
- `Ghi đè`: copy cảnh báo rõ file hiện có sẽ bị thay thế.
- `Đổi tên`: cho server tạo tên an toàn; hiển thị tên cuối cùng trong Completed/history response.
- `Bỏ qua`: không gửi bytes; cách ánh xạ vào bốn trạng thái/history còn chờ xác nhận.
- Không chọn sẵn phương án. Đóng dialog giữ file ở Waiting/Cần xử lý; người dùng
  có thể mở lại từ row. Nếu nhiều conflict, xử lý tuần tự để tránh nhiều dialog
  đồng thời. `Áp dụng cho các tệp trùng còn lại` chỉ tác động tới các conflict đã
  được server phát hiện và vẫn cần thao tác xác nhận của người dùng.

## 4. Connection states

### Online

- Navigation: icon link/check + `Đã kết nối`.
- Không cần success banner thường trực.

### Server offline

- Navigation: broken-link icon + `Mất kết nối`.
- Banner persistent, không modal: `Không thể bắt đầu tệp mới. Các tệp đang chờ vẫn được giữ lại.`
- Action `Thử kết nối` có loading state và disabled trong lúc request đang chạy.
- File đã truyền dở chuyển Failed; file chưa truyền giữ Waiting.
- Đề xuất UX: vẫn cho phép thêm file khi offline để chuẩn bị queue. Tự chạy khi reconnect hay yêu cầu thao tác người dùng cần được xác nhận.

### Reconnecting

- Transient state đề xuất: spinner nhỏ + `Đang kết nối lại…`.
- Spinner đi cùng text; timeout chuyển Offline và cho phép thử lại.

## 5. History states

| State | Hiển thị | Hành động/ghi chú |
|---|---|---|
| Loading history | Skeleton toolbar + 5-6 row, heading vẫn ổn định | Không dùng spinner giữa màn hình; announce `Đang tải lịch sử` |
| Populated | Search, filter, table có thời gian/dung lượng/kết quả | Filter cập nhật count/result; giữ query khi chuyển tab nếu được duyệt |
| Empty history | Icon lịch sử, `Chưa có lịch sử upload`, giải thích ngắn | CTA `Tải tệp` chuyển về Upload workspace |
| No search results | Icon search, `Không tìm thấy tệp phù hợp` | `Xóa tìm kiếm và bộ lọc`; không dùng copy giống empty history |
| History load failed | Error icon, nguyên nhân dễ hiểu | `Thử lại`; không giả vờ empty |

## 6. Summary counters

- `Tổng số tệp` = số item trong current queue/session view, không mặc nhiên là tổng history.
- `Đang tải`, `Đang chờ`, `Thành công`, `Lỗi` phải cộng đúng theo domain state hiện tại.
- Duplicate conflict cần quyết định có tính vào `Đang chờ` hay một warning riêng; khuyến nghị vẫn tính vào Waiting và thêm warning marker, tránh tạo metric thứ sáu.
- Counter cập nhật không làm thay đổi vị trí/focus của action đang dùng.

## 7. Validation feedback

- Validation theo từng file, không toast một câu cho cả lô.
- Nếu file không được thêm vào queue, hiển thị một validation summary ngay dưới drop zone với tên file, lý do và action đóng.
- Tên file dài được ellipsis nhưng tooltip/accessible text giữ full name.
- Không hiển thị full local path trừ khi có yêu cầu kỹ thuật cụ thể; bảo vệ riêng tư và giảm nhiễu.

## 8. Interaction states for controls

Mọi button, nav item, input, filter và row action phải có:

- Default.
- Hover.
- Focus-visible 2px + offset.
- Active/pressed.
- Disabled với text vẫn đọc được.
- Loading khi action bất đồng bộ.
- Error association qua helper text/accessible description khi phù hợp.

Không dùng disabled chỉ bằng giảm opacity quá thấp; contrast text disabled vẫn phải đọc được.

## 9. Announcements and keyboard

- Progress không announce mỗi phần trăm; chỉ announce mốc quan trọng hoặc hoàn tất/lỗi để tránh gây nhiễu.
- Thêm nhiều file: announce tổng số file hợp lệ và số file bị từ chối.
- Conflict: announce tên file và yêu cầu chọn hành động.
- Offline/online: announce một lần khi state thay đổi.
- `Escape` đóng menu/tooltip; không xóa item hoặc bỏ conflict decision.
- `Enter` kích hoạt primary action; `Space` kích hoạt button/drop zone theo convention desktop.

## 10. Cần xác nhận trước implementation

1. `N`, dung lượng tối đa và whitelist định dạng để viết helper/validation copy thật.
2. Có cho phép thêm file khi offline không; reconnect tự chạy hay cần xác nhận.
3. Phạm vi UX cuối cùng của `Áp dụng cho các tệp trùng còn lại` (giữ hay bỏ trước phát hành).
4. Mapping `Bỏ qua` vào state hiện tại, summary và history.
5. Có cho phép Xóa item Completed khỏi current queue; có cần `Xóa tất cả đã hoàn tất` không.
6. File đang Uploading có action hủy không. Nếu không xác nhận, không hiển thị action.
7. History giữ search/filter khi chuyển tab hoặc reset mỗi lần mở.
8. History có pagination/virtualization hay tải toàn bộ; cần số lượng bản ghi điển hình và tối đa.
9. Định dạng thời gian, múi giờ và đơn vị MB/MiB.
10. Có cần hiển thị tên server/host cho người dùng phổ thông hay chỉ trạng thái kết nối.
