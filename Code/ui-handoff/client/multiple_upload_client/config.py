"""Configuration loader for the standalone desktop client."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path

from .limits import MAX_CONCURRENT_UPLOADS, MAX_UPLOAD_SIZE


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"


@dataclass(frozen=True, slots=True)
class ClientConfig:
    transport: str
    tcp_host: str
    tcp_port: int
    base_url: str
    upload_endpoint: str
    allow_mock_fallback: bool
    max_concurrent: int
    max_upload_size: int
    conflict_policy: str

    @classmethod
    def load(cls, config_path: Path = CONFIG_PATH) -> "ClientConfig":
        values: dict[str, object] = {}
        if config_path.exists():
            values = json.loads(config_path.read_text(encoding="utf-8"))

        base_url = os.getenv("UDM10_API_BASE_URL", str(values.get("base_url", "")))
        configured_transport = os.getenv("UDM10_TRANSPORT")
        if configured_transport is None:
            configured_transport = values.get("transport")
        if configured_transport is None or not str(configured_transport).strip():
            transport = "http" if base_url.strip() else "tcp"
        else:
            transport = str(configured_transport).strip().lower()
        if transport not in {"tcp", "http", "mock"}:
            raise ValueError("UDM10_TRANSPORT phải là tcp, http hoặc mock.")

        tcp_host = os.getenv(
            "UDM10_TCP_HOST", str(values.get("tcp_host", "127.0.0.1"))
        ).strip()
        try:
            tcp_port = int(os.getenv("UDM10_TCP_PORT", str(values.get("tcp_port", 9000))))
        except ValueError as error:
            raise ValueError("UDM10_TCP_PORT phải là số nguyên.") from error
        if not tcp_host:
            raise ValueError("UDM10_TCP_HOST không được để trống.")
        if not 1 <= tcp_port <= 65535:
            raise ValueError("UDM10_TCP_PORT phải nằm trong khoảng 1–65535.")

        endpoint = os.getenv(
            "UDM10_UPLOAD_ENDPOINT", str(values.get("upload_endpoint", "/api/uploads"))
        )
        fallback_value = os.getenv(
            "UDM10_ALLOW_MOCK_FALLBACK",
            str(values.get("allow_mock_fallback", False)),
        )
        try:
            max_concurrent = int(
                os.getenv(
                    "UDM10_MAX_CONCURRENT",
                    str(values.get("max_concurrent", 3)),
                )
            )
        except ValueError as error:
            raise ValueError("UDM10_MAX_CONCURRENT phải là số nguyên.") from error
        if not 1 <= max_concurrent <= MAX_CONCURRENT_UPLOADS:
            raise ValueError("UDM10_MAX_CONCURRENT phải nằm trong khoảng 1–3.")

        try:
            max_upload_size = int(
                os.getenv(
                    "UDM10_MAX_UPLOAD_SIZE",
                    str(values.get("max_upload_size", MAX_UPLOAD_SIZE)),
                )
            )
        except ValueError as error:
            raise ValueError("UDM10_MAX_UPLOAD_SIZE phải là số nguyên.") from error
        if not 0 <= max_upload_size <= MAX_UPLOAD_SIZE:
            raise ValueError(
                "UDM10_MAX_UPLOAD_SIZE phải từ 0 đến 524.288.000 byte (500 MB)."
            )

        conflict_policy = os.getenv(
            "UDM10_CONFLICT_POLICY", str(values.get("conflict_policy", "ask"))
        ).strip().lower()
        if conflict_policy not in {"ask", "rename", "overwrite", "skip"}:
            raise ValueError(
                "UDM10_CONFLICT_POLICY phải là ask, rename, overwrite hoặc skip."
            )
        return cls(
            transport=transport,
            tcp_host=tcp_host,
            tcp_port=tcp_port,
            base_url=base_url.rstrip("/"),
            upload_endpoint="/" + endpoint.strip("/"),
            allow_mock_fallback=str(fallback_value).lower() in {"1", "true", "yes", "on"},
            max_concurrent=max_concurrent,
            max_upload_size=max_upload_size,
            conflict_policy=conflict_policy,
        )

    @property
    def upload_url(self) -> str:
        if not self.base_url:
            return ""
        return f"{self.base_url}{self.upload_endpoint}"

    @property
    def mode_label(self) -> str:
        if self.transport == "tcp":
            return f"TCP: {self.tcp_host}:{self.tcp_port}"
        if self.transport == "http":
            return f"HTTP: {self.upload_url or 'chưa cấu hình'}"
        return "Chế độ mô phỏng"
