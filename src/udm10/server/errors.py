"""Stable server errors and their machine-readable wire codes."""

from __future__ import annotations


class UploadError(Exception):
    code = "upload_error"

    def __init__(self, message: str, *, bytes_received: int = 0) -> None:
        super().__init__(message)
        self.bytes_received = bytes_received


class InvalidFilename(UploadError):
    code = "invalid_filename"


class InvalidSize(UploadError):
    code = "invalid_size"


class FileTooLarge(UploadError):
    code = "file_too_large"


class ExtensionNotAllowed(UploadError):
    code = "extension_not_allowed"


class IncompletePayload(UploadError):
    code = "incomplete_payload"


class TransferTimeout(UploadError):
    code = "transfer_timeout"


class StorageFailure(UploadError):
    code = "storage_error"


class DuplicateDetected(UploadError):
    code = "duplicate_conflict"

    def __init__(self, filename: str) -> None:
        super().__init__("Tệp đã tồn tại trên máy chủ.")
        self.filename = filename


class DestinationBusy(UploadError):
    code = "destination_busy"
