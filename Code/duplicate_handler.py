"""
Code/Server/upload/duplicate_handler.py
Phụ trách: TV5 — Trùng tên file

Quy tắc: nếu file trùng tên đã tồn tại trong thư mục lưu trữ, tự động
đổi tên theo dạng name(1).ext, name(2).ext, ...

Toàn bộ thao tác "kiểm tra trùng tên" + "chiếm chỗ tên file" (mở file
để ghi) được thực hiện trong CÙNG MỘT LOCK để tránh race-condition khi
nhiều file trùng tên đến gần như đồng thời (ví dụ 2 client cùng gửi
"report.pdf" cùng lúc).
"""

import os
import threading

# Lock dùng chung cho toàn bộ thao tác resolve + tạo file trên server.
_file_lock = threading.Lock()


def resolve_filename(save_dir: str, filename: str) -> str:
    """
    Trả về một tên file KHÔNG bị trùng trong save_dir.
    Quy tắc: name.ext -> name(1).ext -> name(2).ext -> ...

    Lưu ý: chỉ nên gọi hàm này bên trong _file_lock (xem reserve_file_path)
    để đảm bảo an toàn khi có nhiều luồng cùng xử lý song song.
    """
    base, ext = os.path.splitext(filename)
    candidate = filename
    counter = 1
    while os.path.exists(os.path.join(save_dir, candidate)):
        candidate = f"{base}({counter}){ext}"
        counter += 1
    return candidate


def reserve_file_path(save_dir: str, filename: str):
    """
    "Chiếm chỗ" một tên file hợp lệ (không trùng) và mở sẵn file để ghi.
    Kiểm tra trùng tên + tạo file thực hiện TRONG LOCK để tránh 2 file
    cùng tên bị xử lý sai khi đến đồng thời.

    Trả về: (final_name, file_handle)
    """
    os.makedirs(save_dir, exist_ok=True)
    with _file_lock:
        final_name = resolve_filename(save_dir, filename)
        final_path = os.path.join(save_dir, final_name)
        file_handle = open(final_path, "wb")  # mở ngay để giữ chỗ tên này
    return final_name, file_handle
