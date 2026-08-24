"""Length-prefixed UTF-8 JSON framing for TCP control messages."""

from __future__ import annotations

import json
import socket
import struct
from collections.abc import Mapping
from typing import Any

_HEADER = struct.Struct("!I")


class ProtocolError(ValueError):
    """Raised when a TCP control frame is malformed or unsafe to accept."""


class ConnectionClosed(ConnectionError):
    """Raised when the peer closes cleanly between control frames."""


def encode_message(
    message: Mapping[str, Any], *, max_payload_bytes: int = 1_048_576
) -> bytes:
    """Encode one JSON object with a four-byte big-endian length prefix."""
    try:
        payload = json.dumps(
            dict(message),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProtocolError("Thông điệp không thể mã hóa thành JSON.") from exc

    if not payload:
        raise ProtocolError("Payload JSON không được rỗng.")
    if len(payload) > max_payload_bytes:
        raise ProtocolError("Payload JSON vượt giới hạn control message.")
    return _HEADER.pack(len(payload)) + payload


def receive_message(
    connection: socket.socket, *, max_payload_bytes: int = 1_048_576
) -> dict[str, Any]:
    """Read and decode exactly one framed JSON object."""
    header = _receive_exact(connection, _HEADER.size)
    payload_size = _HEADER.unpack(header)[0]
    if payload_size == 0:
        raise ProtocolError("Payload JSON không được rỗng.")
    if payload_size > max_payload_bytes:
        raise ProtocolError("Payload JSON vượt giới hạn control message.")

    payload = _receive_exact(connection, payload_size)
    try:
        message = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("Payload không phải JSON UTF-8 hợp lệ.") from exc
    if not isinstance(message, dict):
        raise ProtocolError("Thông điệp gốc phải là một JSON object.")
    return message


def send_message(
    connection: socket.socket,
    message: Mapping[str, Any],
    *,
    max_payload_bytes: int = 1_048_576,
) -> None:
    """Encode and send one complete control message."""
    connection.sendall(
        encode_message(message, max_payload_bytes=max_payload_bytes)
    )


def _receive_exact(connection: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = connection.recv(size - len(chunks))
        if not chunk:
            if not chunks:
                raise ConnectionClosed("Kết nối đã đóng.")
            raise ProtocolError("Kết nối đóng giữa chừng control frame.")
        chunks.extend(chunk)
    return bytes(chunks)
