import os
from duplicate_handler import reserve_file_path

# Thư mục lưu file mặc định
SAVE_DIR = os.path.join(os.path.dirname(__file__), "uploads")


def save_incoming_file(save_dir: str, filename: str, data_stream) -> dict:
    """Lưu file từ data stream vào thư mục"""
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
    """Xóa file nếu lưu thất bại"""
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass