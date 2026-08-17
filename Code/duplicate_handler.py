import os
import threading

_file_lock = threading.Lock()


def resolve_filename(save_dir: str, filename: str) -> str:
   
    base, ext = os.path.splitext(filename)
    candidate = filename
    counter = 1
    while os.path.exists(os.path.join(save_dir, candidate)):
        candidate = f"{base}({counter}){ext}"
        counter += 1
    return candidate


def reserve_file_path(save_dir: str, filename: str):
 
    os.makedirs(save_dir, exist_ok=True)
    with _file_lock:
        final_name = resolve_filename(save_dir, filename)
        final_path = os.path.join(save_dir, final_name)
        file_handle = open(final_path, "wb") 
    return final_name, file_handle
