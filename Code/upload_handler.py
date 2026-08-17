import os

from Code.Server.upload.duplicate_handler import reserve_file_path
from Code.Shared.logger_utils import log_event

SAVE_DIR = os.path.join(os.path.dirname(__file__), "..", "storage")


def save_incoming_file(save_dir: str, filename: str, data_stream) -> dict:
 
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

    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError as e:
        log_event(f"Không thể xóa file dở dang '{path}': {e}")


def handle_single_file_upload(file_meta: dict, data_stream, send_status_fn) -> None:

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
