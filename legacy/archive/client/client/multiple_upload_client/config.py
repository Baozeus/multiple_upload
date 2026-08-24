"""Configuration loader for the standalone desktop client."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"


@dataclass(frozen=True, slots=True)
class ClientConfig:
    base_url: str
    upload_endpoint: str
    allow_mock_fallback: bool

    @classmethod
    def load(cls, config_path: Path = CONFIG_PATH) -> "ClientConfig":
        values: dict[str, object] = {}
        if config_path.exists():
            values = json.loads(config_path.read_text(encoding="utf-8"))

        base_url = os.getenv("UDM10_API_BASE_URL", str(values.get("base_url", "")))
        endpoint = os.getenv(
            "UDM10_UPLOAD_ENDPOINT", str(values.get("upload_endpoint", "/api/uploads"))
        )
        fallback_value = os.getenv(
            "UDM10_ALLOW_MOCK_FALLBACK",
            str(values.get("allow_mock_fallback", True)),
        )
        return cls(
            base_url=base_url.rstrip("/"),
            upload_endpoint="/" + endpoint.strip("/"),
            allow_mock_fallback=str(fallback_value).lower() in {"1", "true", "yes", "on"},
        )

    @property
    def upload_url(self) -> str:
        if not self.base_url:
            return ""
        return f"{self.base_url}{self.upload_endpoint}"
