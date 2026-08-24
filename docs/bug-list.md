# Bug list

Ngày kiểm thử: 2026-08-24. Không còn bug mở mức Critical/High/Medium/Low sau
regression.

| ID | Mức | Thành phần | Hiện tượng | Nguyên nhân | Sửa | Trạng thái |
|---|---|---|---|---|---|---|
| BUG-001 | Low | UI/ProgressBar | Qt phát cảnh báo `Unknown property font-variant-numeric` lặp theo số dòng | QSS không hỗ trợ thuộc tính CSS web này | Bỏ thuộc tính không hợp lệ, giữ `font-weight` | Closed |

## Ghi chú triage

- Assertion focus ban đầu thất bại trên Qt offscreen vì plugin không duy trì
  global focus widget. Đây không phải bug sản phẩm; test được sửa để kiểm hành
  vi bàn phím thực tế: Space trên nút Lịch sử phải đổi trang.
- Các giới hạn dung lượng/định dạng trống là quyết định chưa xác nhận, không
  được ghi thành bug hoặc tự đặt chỉ để test pass.
