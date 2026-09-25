"""Validated MySQL settings without embedding credentials in source code."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MySqlSettings:
    host: str
    port: int
    database: str
    user: str
    password: str

    def __post_init__(self) -> None:
        if not self.host.strip():
            raise ValueError("MYSQL_HOST không được để trống.")
        if not 1 <= self.port <= 65535:
            raise ValueError("MYSQL_PORT phải nằm trong khoảng 1–65535.")
        if not self.database.strip():
            raise ValueError("MYSQL_DATABASE không được để trống.")
        if not self.user.strip():
            raise ValueError("MYSQL_USER không được để trống.")
