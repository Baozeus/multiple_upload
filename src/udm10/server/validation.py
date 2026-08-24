"""Untrusted upload metadata validation and Unicode filename normalization."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import replace
from pathlib import Path, PurePath

from udm10.config import UploadPolicySettings
from udm10.domain import UploadRequest
from udm10.server.errors import (
    ExtensionNotAllowed,
    FileTooLarge,
    InvalidFilename,
    InvalidSize,
)

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_WINDOWS_ILLEGAL_CHARS = re.compile(r"[<>:\"/\\|?*]")
_WINDOWS_RESERVED = {
    "con", "prn", "aux", "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}


class UploadValidator:
    """Validate one request; callers receive a normalized safe filename."""

    def __init__(self, policy: UploadPolicySettings, *, max_filename_bytes: int = 255):
        self._policy = policy
        self._max_filename_bytes = max_filename_bytes

    def validate(self, request: UploadRequest) -> UploadRequest:
        filename = _normalize_filename(request.filename, self._max_filename_bytes)
        if request.size < 0:
            raise InvalidSize("Dung lượng tệp không được âm.")
        if self._policy.max_file_size_mb is not None:
            limit = self._policy.max_file_size_mb * 1024 * 1024
            if request.size > limit:
                raise FileTooLarge("Tệp vượt giới hạn dung lượng của máy chủ.")
        allowed = self._policy.allowed_extensions
        if allowed is not None and Path(filename).suffix.casefold() not in {
            extension.casefold() for extension in allowed
        }:
            raise ExtensionNotAllowed("Định dạng tệp không được máy chủ cho phép.")
        return replace(request, filename=filename)


def _normalize_filename(filename: str, max_bytes: int) -> str:
    normalized = unicodedata.normalize("NFC", filename).strip()
    if not normalized or normalized in {".", ".."}:
        raise InvalidFilename("Tên tệp không được rỗng hoặc là đường dẫn tương đối.")
    if PurePath(normalized).is_absolute() or "/" in normalized or "\\" in normalized:
        raise InvalidFilename("Tên tệp không được chứa đường dẫn.")
    if _WINDOWS_ILLEGAL_CHARS.search(normalized) or _CONTROL_CHARS.search(normalized):
        raise InvalidFilename("Tên tệp chứa ký tự không an toàn.")
    if normalized.endswith((".", " ")):
        raise InvalidFilename("Tên tệp không được kết thúc bằng dấu chấm hoặc khoảng trắng.")
    stem = normalized.split(".", 1)[0].casefold()
    if stem in _WINDOWS_RESERVED:
        raise InvalidFilename("Tên tệp là tên thiết bị dành riêng của hệ điều hành.")
    if len(normalized.encode("utf-8")) > max_bytes:
        raise InvalidFilename("Tên tệp vượt giới hạn 255 byte UTF-8.")
    return normalized
