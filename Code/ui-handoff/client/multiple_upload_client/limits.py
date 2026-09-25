"""Confirmed client-side admission limits for UDM_10."""

MAX_CONCURRENT_UPLOADS = 3
MAX_FILES_PER_SELECTION = 6
MAX_UPLOAD_SIZE = 500 * 1024  # 500 KiB = 512,000 bytes
ALLOWED_EXTENSIONS = frozenset({".txt", ".pdf", ".jpg", ".jpeg", ".doc", ".docx"})
