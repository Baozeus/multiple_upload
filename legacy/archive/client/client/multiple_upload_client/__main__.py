"""Run the UDM_10 desktop client with ``python -m multiple_upload_client``."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .config import ClientConfig
from .main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Multiple Upload")
    app.setOrganizationName("UDM_10")
    window = MainWindow(ClientConfig.load())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
