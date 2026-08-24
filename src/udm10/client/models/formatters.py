"""Locale-stable presentation formatting shared across desktop views."""

from __future__ import annotations

from datetime import datetime


def format_bytes(size_bytes: int) -> str:
    value = float(max(0, size_bytes))
    units = ("B", "KB", "MB", "GB", "TB")
    unit = units[0]
    for unit in units:
        if value < 1000.0 or unit == units[-1]:
            break
        value /= 1000.0
    if unit == "B":
        return f"{int(value)} {unit}"
    decimals = 0 if value >= 100 else 1
    return f"{value:.{decimals}f}".replace(".", ",") + f" {unit}"


def format_speed(bytes_per_second: float) -> str:
    if bytes_per_second <= 0:
        return "—"
    return f"{format_bytes(int(bytes_per_second))}/s"


def format_datetime(value: datetime) -> str:
    return value.strftime("%d/%m/%Y %H:%M")
