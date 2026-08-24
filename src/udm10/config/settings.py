"""Typed, side-effect-free configuration loaded from environment variables."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class TcpSettings:
    bind_host: str
    client_host: str
    port: int
    max_control_message_bytes: int
    socket_timeout_seconds: float = 15.0
    file_chunk_size_bytes: int = 64 * 1024


@dataclass(frozen=True, slots=True)
class MySqlSettings:
    enabled: bool
    host: str
    port: int
    database: str
    user: str
    password: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class HistorySettings:
    backend: str
    json_path: Path
    mysql: MySqlSettings


@dataclass(frozen=True, slots=True)
class UploadPolicySettings:
    max_concurrent_uploads: int | None
    max_file_size_mb: int | None
    allowed_extensions: tuple[str, ...] | None


@dataclass(frozen=True, slots=True)
class AppSettings:
    tcp: TcpSettings
    history: HistorySettings
    upload_policy: UploadPolicySettings
    upload_dir: Path
    log_dir: Path
    log_level: str


def load_settings(env: Mapping[str, str] | None = None) -> AppSettings:
    """Load settings without requiring a `.env` parser during imports/tests."""
    if env is None:
        try:
            from dotenv import load_dotenv
        except ImportError:
            pass
        else:
            load_dotenv(PROJECT_ROOT / ".env")
    values = os.environ if env is None else env
    mysql_enabled = _as_bool(values.get("MYSQL_ENABLED", "false"))

    mysql = MySqlSettings(
        enabled=mysql_enabled,
        host=values.get("MYSQL_HOST", "127.0.0.1"),
        port=_positive_int(values.get("MYSQL_PORT", "3306"), "MYSQL_PORT"),
        database=values.get("MYSQL_DATABASE", "udm_10"),
        user=values.get("MYSQL_USER", ""),
        password=values.get("MYSQL_PASSWORD", ""),
    )
    history = HistorySettings(
        backend="mysql" if mysql_enabled else "json",
        json_path=_project_path(
            values.get("HISTORY_JSON_PATH", "database/history.json")
        ),
        mysql=mysql,
    )
    tcp = TcpSettings(
        bind_host=values.get("TCP_BIND_HOST", "127.0.0.1"),
        client_host=values.get("TCP_HOST", "127.0.0.1"),
        port=_port(values.get("TCP_PORT", "9000"), "TCP_PORT"),
        max_control_message_bytes=_positive_int(
            values.get("TCP_CONTROL_MAX_BYTES", "1048576"),
            "TCP_CONTROL_MAX_BYTES",
        ),
        socket_timeout_seconds=_positive_float(
            values.get("TCP_SOCKET_TIMEOUT_SECONDS", "15"),
            "TCP_SOCKET_TIMEOUT_SECONDS",
        ),
        file_chunk_size_bytes=_positive_int(
            values.get("TCP_FILE_CHUNK_BYTES", "65536"),
            "TCP_FILE_CHUNK_BYTES",
        ),
    )
    upload_policy = UploadPolicySettings(
        max_concurrent_uploads=_optional_positive_int(
            values.get("MAX_CONCURRENT_UPLOADS", "3"), "MAX_CONCURRENT_UPLOADS"
        ),
        max_file_size_mb=_optional_positive_int(
            values.get("MAX_FILE_SIZE_MB"), "MAX_FILE_SIZE_MB"
        ),
        allowed_extensions=_extensions(values.get("ALLOWED_EXTENSIONS")),
    )
    return AppSettings(
        tcp=tcp,
        history=history,
        upload_policy=upload_policy,
        upload_dir=_project_path(values.get("UPLOAD_DIR", "uploads")),
        log_dir=_project_path(values.get("LOG_DIR", "logs")),
        log_level=values.get("LOG_LEVEL", "INFO").upper(),
    )


def _project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _as_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError("Giá trị boolean cấu hình không hợp lệ.")


def _positive_int(value: str, name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} phải là số nguyên.") from exc
    if parsed <= 0:
        raise ValueError(f"{name} phải lớn hơn 0.")
    return parsed


def _positive_float(value: str, name: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{name} phải là số.") from exc
    if parsed <= 0:
        raise ValueError(f"{name} phải lớn hơn 0.")
    return parsed


def _optional_positive_int(value: str | None, name: str) -> int | None:
    if value is None or not value.strip():
        return None
    return _positive_int(value, name)


def _port(value: str, name: str) -> int:
    parsed = _positive_int(value, name)
    if parsed > 65_535:
        raise ValueError(f"{name} phải nhỏ hơn hoặc bằng 65535.")
    return parsed


def _extensions(value: str | None) -> tuple[str, ...] | None:
    if value is None or not value.strip():
        return None
    extensions = []
    for raw_extension in value.split(","):
        extension = raw_extension.strip().lower()
        if not extension:
            continue
        extensions.append(extension if extension.startswith(".") else f".{extension}")
    return tuple(dict.fromkeys(extensions)) or None
