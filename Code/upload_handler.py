import os
from duplicate_handler import abort_reserved_file, commit_file, reserve_file_path

# Thư mục lưu file mặc định
SAVE_DIR = os.path.join(os.path.dirname(__file__), "uploads")


def save_incoming_file(
    save_dir: str, filename: str, data_stream, conflict: str = "rename"
) -> dict:
    """Lưu file từ data stream vào thư mục"""
    reservation = reserve_file_path(save_dir, filename, conflict)
    if reservation is None:
        return {
            "final_name": filename,
            "completed": False,
            "skipped": True,
            "bytes_written": 0,
        }

    return save_reserved_file(reservation, data_stream)


def save_reserved_file(reservation, data_stream) -> dict:
    """Ghi vào một đích đã được dành trước khi Server gửi ACK."""
    f = reservation["file"]
    bytes_written = 0

    try:
        for chunk in data_stream:
            if not chunk:
                continue
            f.write(chunk)
            bytes_written += len(chunk)
        f.close()
        if not commit_file(reservation):
            _remove_partial_file(reservation["temporary_path"])
            return {
                "final_name": reservation["final_name"],
                "completed": False,
                "skipped": True,
                "bytes_written": bytes_written,
            }
        return {
            "final_name": reservation["final_name"],
            "completed": True,
            "skipped": False,
            "bytes_written": bytes_written,
        }
    except Exception:
        abort_reserved_file(reservation)
        raise


def _remove_partial_file(path: str) -> None:
    """Xóa file nếu lưu thất bại"""
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
