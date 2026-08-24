"""Central logging setup for both processes."""

from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(level: str, log_dir: Path) -> None:
    """Configure console and rotating-process file logging once."""
    log_dir.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        logging.FileHandler(log_dir / "udm10.log", encoding="utf-8"),
    ]
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=handlers,
        force=True,
    )
