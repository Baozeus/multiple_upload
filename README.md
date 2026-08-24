# multiple_upload

## Chạy bản Client giao diện mới

Client PySide6 trong `Code/ui-handoff/client` dùng TCP mặc định và kết nối trực tiếp với `Code/server.py`. HTTP Adapter vẫn được giữ để tương thích cấu hình cũ.

```powershell
python -m pip install -r Code\ui-handoff\client\requirements.txt
python Code\server.py --host 127.0.0.1 --port 9000
python Code\ui-handoff\client\run.py
```

Xem cấu hình và cơ chế tương thích tại `Code/ui-handoff/client/README.md`.

Chạy kiểm thử từ thư mục gốc repository:

```powershell
python -B -m unittest discover -s Code\tests -v
```

## Thành viên : 
* Người 1 : Nguyễn Tấn Bão 
* Người 2 : Nguyễn Phi Long 
* Người 3 : Nguyễn Viết Thịnh 
* Người 4 : Nguyễn Đặng Xuân Phát 
* Người 5 : Phạm Trần Đức Phú 
* Người 6 : Phạm Ngọc Phú 
## Ngôn ngữ : 
* Python
### KẾ HOẠCH PHÂN BỐ NHÂN SỰ DỰ ÁN
UDM_10 — Upload nhiều file
1. Thông tin dự án
Project Code: UDM_10
Mô tả: Ứng dụng GUI cho phép kéo thả và upload nhiều file lên Server.
Số thành viên thực hiện: 6
2. Tóm tắt yêu cầu cốt lõi
-Kéo-thả một hoặc nhiều file vào khu vực upload trên GUI
- Mỗi file có trạng thái riêng: chờ → đang tải → hoàn tất / lỗi
- Hiển thị tốc độ và tiến trình (%) riêng cho từng file
- Hỗ trợ hàng đợi hoặc upload đồng thời có giới hạn số file cùng lúc
- Lỗi của một file không được làm dừng các file còn lại
- Có quy tắc xử lý file trùng tên trên Server
- Không bắt buộc Pause/Resume (tránh trùng phạm vi với UDM_12)
#  Lộ trình dự án (4 Tuần)

### Tuần 1 — Phân tích & Thiết kế
| Thành viên | Việc cần làm |
| :---: | :--- |
| **TV1** | Vẽ sơ đồ kiến trúc hệ thống, thiết kế API, setup project skeleton |
| **TV2** | Thiết kế state machine cho file, phác thảo UI progress bar |
| **TV3** | Chọn công nghệ server, setup server rỗng, test nhận 1 file đơn giản |
| **TV4** | Nghiên cứu cơ chế hàng đợi, viết pseudo-code |
| **TV5** | Đề xuất quy tắc trùng tên |
| **TV6** | Soạn checklist test case dựa trên 7 yêu cầu trong đề bài |

### Tuần 2 — Phát triển module riêng lẻ
| Thành viên | Việc cần làm |
| :---: | :--- |
| **TV1** | Code vùng kéo-thả hoạt động được, hỗ trợ chọn nhiều file cùng lúc |
| **TV2** | Code progress bar + hiển thị % và tốc độ cho từng dòng file riêng biệt |
| **TV3** | Hoàn thiện API nhận file thật, lưu đúng thư mục, trả JSON kết quả |
| **TV4** | Code logic hàng đợi hoạt động: khi vượt giới hạn file cùng lúc thì file mới phải ở trạng thái "chờ" |
| **TV5** | Code xử lý trùng tên trên server + đảm bảo lỗi của 1 file không làm dừng tiến trình các file khác |
| **TV6** | Bắt đầu test từng module riêng lẻ khi các bạn hoàn thành, ghi log lỗi để báo lại |

### Tuần 3 — Tích hợp & Kiểm thử
| Thành viên | Việc cần làm |
| :---: | :--- |
| **TV1** | Ghép giao diện kéo-thả với module trạng thái (TV2) thành một luồng UI hoàn chỉnh |
| **TV2** | Kết nối tiến trình thực tế từ server (TV3) để progress bar chạy đúng dữ liệu thật |
| **TV3** | Phối hợp TV4, TV5 để server xử lý đúng: nhận đồng thời có giới hạn + xử lý trùng tên |
| **TV4** | Test cơ chế hàng đợi với nhiều file thật |
| **TV5** | Test tình huống lỗi: ngắt mạng giữa chừng, file trùng tên, file quá lớn — đảm bảo các file khác vẫn tiếp tục |
| **TV6** | Chạy full test case theo checklist, lập bảng lỗi (bug list) gửi từng người sửa |

### Tuần 4 — Hoàn thiện & Báo cáo
| Thành viên | Việc cần làm |
| :---: | :--- |
| **Tất cả** | Sửa lỗi theo bug list của TV6, tối ưu UI/UX |
| **TV1** | Chốt bản demo cuối, kiểm tra kiến trúc tổng thể |
| **TV6** | Viết báo cáo dự án + làm slide thuyết trình, tổng hợp đóng góp từng thành viên |
| **Cả nhóm** | Diễn tập demo (kéo nhiều file, show từng trạng thái, show 1 file lỗi không ảnh hưởng file khác, show xử lý trùng tên) |

