import json
import os
import re
import socket

HEADER_MAX = 64 * 1024
CHUNK_SIZE = 4096
DEFAULT_TIMEOUT = 5.0
DEFAULT_PORT = 9000

SAFE_NAME = re.compile(r"^[\w.\- ()\[\]]+$", re.UNICODE)


def send_json(sock, payload):
    """Gửi JSON: trước là 4 byte đỗ lại, sau là nội dung."""
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if len(raw) > HEADER_MAX:
        raise ValueError("JSON quá lớn")
    sock.sendall(len(raw).to_bytes(4, "big") + raw)


def recv_exact(sock, n):
    """Nhận đúng n byte (lặp lại đến khi đủ)."""    
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Mất kết nối khi đang nhận data")
        buf += chunk
    return buf


def recv_json(sock):
    """Nhận JSON: đọc 4 byte độ dài rồi đọc body."""
    length = int.from_bytes(recv_exact(sock, 4), "big")
    if length <= 0 or length > HEADER_MAX:
        raise ValueError("Độ dài JSON không hợp lệ")
    raw = recv_exact(sock, length)
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON phai la object")
    return data


def sanitize_filename(name):
    """Chỉ lấy tên file an toàn (không path traversal)."""
    base = os.path.basename(name.replace("\\", "/").strip())
    if not base or base in (".", ".."):
        raise ValueError("Tên file không hợp lệ")
    if len(base) > 255:
        raise ValueError("Tên file quá dài")
    if not SAFE_NAME.match(base):
        raise ValueError("Tên file chứa ký tự không hợp lệ")
    return base


def validate_upload_header(header):
    """Kiểm tra header từ Client. Trả về (filename, filesize)."""
    if "filename" not in header or "filesize" not in header:
        raise ValueError("Thiếu filename hoặc filesize")
    filename = sanitize_filename(str(header["filename"]))
    try:
        filesize = int(header["filesize"])
    except (TypeError, ValueError):
        raise ValueError("filesize phai la so nguyen")
    if filesize < 0:
        raise ValueError("filesize phai >= 0")
    if filesize > 10 * 1024 * 1024 * 1024:
        raise ValueError("File qua lon (max 10GB)")
    return filename, filesize


def format_size(num_bytes):
    """Đổi byte sang KB/MB để hiển thị."""
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            if unit == "B":
                return str(int(value)) + " B"
            return "{:.1f} {}".format(value, unit)
        value /= 1024
    return str(num_bytes) + " B"


def format_speed(bytes_per_sec):
    if bytes_per_sec <= 0:
        return "-"
    return format_size(int(bytes_per_sec)) + "/s"
