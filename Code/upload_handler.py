"""
Code/Server/upload/upload_handler.py
Phụ trách: TV5 — Cô lập lỗi cho từng file upload

Nhiệm vụ:
- Lưu dữ liệu file nhận từ Client (kết hợp module duplicate_handler để
  xử lý trùng tên).
- Đảm bảo lỗi của MỘT file (mất kết nối, dữ liệu hỏng, lỗi không xác
  định...) không làm ảnh hưởng / dừng các file khác đang xử lý song song.
- Dữ liệu chưa truyền hoàn tất KHÔNG được công nhận là dữ liệu hoàn
  chỉnh -> tự động xóa file dở dang khi có lỗi giữa chừng.

LƯU Ý TÍCH HỢP:
- TV3 (Server nhận file) gọi handle_single_file_upload() cho mỗi file,
  truyền vào data_stream đọc thật từ socket.
- TV4 (Hàng đợi) phải đảm bảo mỗi file chạy trong 1 thread/task RIÊNG
  (ThreadPoolExecutor, threading.Thread...) thì việc cô lập lỗi ở đây
  mới thực sự có tác dụng.
- TV1 (Protocol/message): điều chỉnh lại nội dung message trong
  status_sender.py cho khớp cấu trúc chung cả nhóm.
"""

import os

from Code.Server.upload.duplicate_handler import reserve_file_path
from Code.Shared.logger_utils import log_event

SAVE_DIR = os.path.join(os.path.dirname(__file__), "..", "storage")


def save_incoming_file(save_dir: str, filename: str, data_stream) -> dict:
    """
    Lưu 1 file nhận từ Client vào save_dir, tự động xử lý trùng tên.

    data_stream: iterable sinh ra các chunk bytes (đại diện cho dữ liệu
    nhận qua socket theo từng phần, do TV3 cung cấp).

    Trả về dict: {"final_name", "completed", "bytes_written"}.
    Nếu bị gián đoạn giữa chừng, file dở dang sẽ bị xóa và exception
    được raise lại để handle_single_file_upload() xử lý & cô lập lỗi.
    """
    final_name, f = reserve_file_path(save_dir, filename)
    final_path = os.path.join(save_dir, final_name)
    bytes_written = 0

    try:
        for chunk in data_stream:
            if not chunk:
                continue
            f.write(chunk)
            bytes_written += len(chunk)
        f.close()
        return {
            "final_name": final_name,
            "completed": True,
            "bytes_written": bytes_written,
        }
    except Exception:
        try:
            f.close()
        finally:
            _remove_partial_file(final_path)
        raise


def _remove_partial_file(path: str) -> None:
    """Xóa file dở dang nếu tồn tại — không công nhận dữ liệu chưa hoàn tất."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError as e:
        log_event(f"Không thể xóa file dở dang '{path}': {e}")


def handle_single_file_upload(file_meta: dict, data_stream, send_status_fn) -> None:
    """
    Xử lý upload cho ĐÚNG MỘT file, hoàn toàn độc lập với các file khác.
    TV3/TV4 gọi hàm này bên trong 1 thread/task riêng cho mỗi file.

    file_meta: {"id": <định danh file>, "name": <tên file gốc>}
    data_stream: generator/iterator sinh ra các chunk bytes của file này.
    send_status_fn: callback gửi trạng thái về Client, chữ ký:
        send_status_fn(file_id, status, reason=None, saved_as=None)

    Hàm này KHÔNG bao giờ để exception văng ra ngoài — mọi lỗi được bắt,
    log lại, báo cho client, và không ảnh hưởng file khác đang chạy song song.
    """
    file_id = file_meta.get("id")
    filename = file_meta.get("name", "unknown_file")

    try:
        result = save_incoming_file(SAVE_DIR, filename, data_stream)
        log_event(
            f"OK - file='{filename}' -> saved_as='{result['final_name']}' "
            f"bytes={result['bytes_written']} id={file_id}"
        )
        send_status_fn(file_id, status="hoàn tất", saved_as=result["final_name"])

    except (ConnectionError, TimeoutError) as e:
        log_event(f"LOI_MANG - file='{filename}' id={file_id} reason={e}")
        send_status_fn(file_id, status="lỗi", reason=f"Mất kết nối: {e}")

    except OSError as e:
        log_event(f"LOI_IO - file='{filename}' id={file_id} reason={e}")
        send_status_fn(file_id, status="lỗi", reason=f"Lỗi lưu trữ: {e}")

    except Exception as e:
        log_event(f"LOI_KHONG_XAC_DINH - file='{filename}' id={file_id} reason={e}")
        send_status_fn(file_id, status="lỗi", reason="Lỗi không xác định")
