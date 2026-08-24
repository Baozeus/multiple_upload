"""PySide6 application bootstrap.

Framework imports stay inside ``main`` so importing the entry point does not
require optional runtime dependencies to be installed yet.
"""

from __future__ import annotations

import sys

from udm10.config import load_settings
from udm10.utils.logging import configure_logging


def main() -> int:
    """Start the production UI with the canonical TCP upload adapter."""
    settings = load_settings()
    configure_logging(settings.log_level, settings.log_dir)

    try:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        from udm10.client.controllers import ApplicationController
        from udm10.client.models.tcp_provider import TcpUploadProvider
        from udm10.client.transports import TcpUploadClient
        from udm10.client.ui.main_window import MainWindow
    except ImportError:
        import logging

        logging.getLogger(__name__).error(
            "PySide6 chưa được cài. Hãy cài requirements.txt trước khi chạy GUI."
        )
        return 2

    app = QApplication.instance() or QApplication(sys.argv)
    max_concurrent = settings.upload_policy.max_concurrent_uploads
    if max_concurrent is None:
        import logging

        logging.getLogger(__name__).error(
            "MAX_CONCURRENT_UPLOADS phải được cấu hình trước khi chạy client."
        )
        return 2
    window = MainWindow(
        server_host=settings.tcp.client_host,
        server_port=settings.tcp.port,
    )
    uploader = TcpUploadClient(
        host=settings.tcp.client_host,
        port=settings.tcp.port,
        timeout_seconds=settings.tcp.socket_timeout_seconds,
        max_control_message_bytes=settings.tcp.max_control_message_bytes,
        chunk_size_bytes=settings.tcp.file_chunk_size_bytes,
    )
    provider = TcpUploadProvider(
        max_concurrent=max_concurrent,
        uploader=uploader,
        parent=app,
    )
    controller = ApplicationController(window, provider, parent=app)
    app.setProperty("udm10Controller", controller)
    app.aboutToQuit.connect(provider.shutdown)
    QTimer.singleShot(0, provider.retry_connection)
    QTimer.singleShot(0, provider.refresh_history)
    window.show()
    return app.exec()
