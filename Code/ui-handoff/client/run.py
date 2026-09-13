"""Convenient entry point for running the desktop client from any working directory."""

from __future__ import annotations

import sys
from pathlib import Path

CLIENT_ROOT = Path(__file__).resolve().parent
if str(CLIENT_ROOT) not in sys.path:
    sys.path.insert(0, str(CLIENT_ROOT))

from multiple_upload_client.__main__ import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
