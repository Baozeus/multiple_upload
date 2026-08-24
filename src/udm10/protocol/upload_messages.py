"""Typed interpretation and construction of upload control messages."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from udm10.domain import ConflictPolicy, StoredFile, UploadRequest
from udm10.protocol.framing import ProtocolError


def parse_upload_start(message: Mapping[str, Any]) -> UploadRequest:
    if message.get("type") != "upload.start":
        raise ProtocolError("Thông điệp không phải upload.start.")
    request_id = message.get("request_id")
    batch_id = message.get("batch_id", request_id)
    batch_total = message.get("batch_total", 1)
    filename = message.get("filename")
    size = message.get("size")
    conflict = message.get("conflict")
    if not isinstance(request_id, str) or not request_id.strip():
        raise ProtocolError("request_id phải là chuỗi không rỗng.")
    if not isinstance(filename, str):
        raise ProtocolError("filename phải là chuỗi.")
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ProtocolError("batch_id phải là chuỗi không rỗng.")
    if (
        isinstance(batch_total, bool)
        or not isinstance(batch_total, int)
        or batch_total <= 0
    ):
        raise ProtocolError("batch_total phải là số nguyên lớn hơn 0.")
    if isinstance(size, bool) or not isinstance(size, int):
        raise ProtocolError("size phải là số nguyên.")
    policy: ConflictPolicy | None = None
    if conflict is not None:
        try:
            policy = ConflictPolicy(conflict)
        except (TypeError, ValueError) as exc:
            raise ProtocolError("conflict phải là overwrite, rename hoặc skip.") from exc
    return UploadRequest(
        request_id.strip(), batch_id.strip(), batch_total, filename, size, policy
    )


def upload_ready(request_id: str) -> dict[str, Any]:
    return {"type": "upload.ready", "request_id": request_id}


def upload_conflict(request_id: str, filename: str) -> dict[str, Any]:
    return {
        "type": "upload.conflict",
        "request_id": request_id,
        "filename": filename,
    }


def upload_completed(request_id: str, stored: StoredFile) -> dict[str, Any]:
    return {
        "type": "upload.result",
        "request_id": request_id,
        "status": "completed",
        "filename": stored.filename,
        "bytes_received": stored.bytes_received,
    }


def upload_skipped(request_id: str, filename: str) -> dict[str, Any]:
    return {
        "type": "upload.result",
        "request_id": request_id,
        "status": "skipped",
        "filename": filename,
        "bytes_received": 0,
    }


def upload_failed(
    request_id: str | None,
    *,
    code: str,
    message: str,
    bytes_received: int = 0,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "upload.result",
        "status": "failed",
        "code": code,
        "message": message,
        "bytes_received": bytes_received,
    }
    if request_id is not None:
        result["request_id"] = request_id
    return result
