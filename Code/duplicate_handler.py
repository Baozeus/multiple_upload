import os
import tempfile
import threading

_file_lock = threading.Lock()
_reserved_paths = set()


def resolve_filename(save_dir: str, filename: str) -> str:
    base, ext = os.path.splitext(filename)
    candidate = filename
    counter = 1
    while _path_is_taken(os.path.join(save_dir, candidate)):
        candidate = f"{base}({counter}){ext}"
        counter += 1
    return candidate


def reserve_file_path(save_dir: str, filename: str, conflict: str = "rename"):
    """Dành một đích ghi và file tạm, không làm hỏng file hiện hữu khi lỗi."""
    os.makedirs(save_dir, exist_ok=True)
    with _file_lock:
        if conflict == "rename":
            final_name = resolve_filename(save_dir, filename)
        else:
            final_name = filename
        final_path = os.path.join(save_dir, final_name)
        if conflict == "skip" and _path_is_taken(final_path):
            return None
        if final_path in _reserved_paths:
            raise RuntimeError("Tệp này đang được một upload khác xử lý")
        _reserved_paths.add(final_path)

    descriptor = None
    temporary_path = None
    try:
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=".udm10-upload-", suffix=".part", dir=save_dir
        )
        file_handle = os.fdopen(descriptor, "wb")
        descriptor = None
    except Exception:
        if descriptor is not None:
            os.close(descriptor)
        if temporary_path:
            try:
                os.remove(temporary_path)
            except OSError:
                pass
        with _file_lock:
            _reserved_paths.discard(final_path)
        raise
    return {
        "final_name": final_name,
        "final_path": final_path,
        "temporary_path": temporary_path,
        "file": file_handle,
        "conflict": conflict,
    }


def commit_file(reservation):
    """Đưa file tạm vào đích bằng thao tác nguyên tử trong cùng filesystem."""
    final_path = reservation["final_path"]
    temporary_path = reservation["temporary_path"]
    conflict = reservation["conflict"]
    try:
        with _file_lock:
            if conflict == "skip" and os.path.exists(final_path):
                return False
            os.replace(temporary_path, final_path)
        return True
    finally:
        release_file(reservation)


def release_file(reservation):
    final_path = reservation["final_path"]
    with _file_lock:
        _reserved_paths.discard(final_path)


def _path_is_taken(path: str) -> bool:
    return os.path.exists(path) or path in _reserved_paths
