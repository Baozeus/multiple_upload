# Phân công và đóng góp

## Nguyên tắc đối chiếu

Bảng dưới đối chiếu checklist PDF với kế hoạch DOCX. Đây là mô tả phân công,
không phải bằng chứng xác nhận đóng góp thực tế. Hai nguồn không đồng nhất và
DOCX không ghi tên thành viên, vì vậy quyết định cuối là **Cần xác nhận**; dự án
không tự chọn một phiên bản.

| TV | PDF: tên và phụ trách chính | DOCX: vai trò/module | Trạng thái |
|---|---|---|---|
| TV1 | Phạm Ngọc Phú — kéo-thả, chọn file, validation UI | Không ghi tên — Nhóm trưởng/Kiến trúc; tổng thể + drag-drop | Cần xác nhận |
| TV2 | Nguyễn Viết Thịnh — trạng thái, tiến trình, tốc độ | Không ghi tên — Dev Frontend/Trạng thái | Cần xác nhận |
| TV3 | Nguyễn Tấn Bão — API upload, lưu file, phản hồi Server | Không ghi tên — Dev Backend/Server; endpoint multipart | Cần xác nhận |
| TV4 | Phạm Trần Đức Phú — FIFO, giới hạn upload đồng thời | Không ghi tên — Dev Backend/Hàng đợi | Cần xác nhận |
| TV5 | Nguyễn Phi Long — lỗi, mất mạng, trùng tên, thử lại | Không ghi tên — Dev Backend/Xử lý lỗi và trùng tên | Cần xác nhận |
| TV6 | Nguyễn Đăng Xuân Phát — lịch sử, regression, bug list | Không ghi tên — QA/Tổng hợp; test, báo cáo, slide/demo | Cần xác nhận |

## Khác biệt cần lưu ý

- PDF cung cấp tên, owner TC và người phối hợp; DOCX chỉ có nhãn TV/vai trò.
- DOCX giao TV1 định nghĩa API và TV3 endpoint `multipart/form-data`; dự án đã
  xác nhận TCP canonical, không triển khai HTTP.
- PDF giao TV6 TC-27..TC-33 gồm lịch sử; DOCX mô tả TV6 rộng hơn về QA/báo cáo.
- TV5 trong PDF có cả mất mạng/thử lại; DOCX nhấn mạnh backend lỗi/trùng tên.

## Owner kiểm thử theo PDF

- TV1: TC-01..TC-06
- TV2: TC-07..TC-11
- TV3: TC-12..TC-14
- TV4: TC-15..TC-19
- TV5: TC-20..TC-26
- TV6: TC-27..TC-33

Tên, vai trò cuối cùng và tỷ lệ đóng góp thực tế: **Cần xác nhận bởi nhóm**.
