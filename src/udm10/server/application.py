"""TCP server process bootstrap."""

from __future__ import annotations

import logging

from udm10.config import load_settings
from udm10.persistence import (
    PersistenceError,
    create_history_repository,
)
from udm10.server.tcp_server import create_server
from udm10.utils.logging import configure_logging


def main() -> int:
    """Run the control-plane TCP server until interrupted."""
    settings = load_settings()
    configure_logging(settings.log_level, settings.log_dir)
    logger = logging.getLogger(__name__)

    try:
        history_repository = create_history_repository(settings.history)
    except PersistenceError as exc:
        logger.critical("Không thể khởi động persistence: %s", exc)
        return 2

    try:
        server = create_server(
            settings.tcp,
            upload_dir=settings.upload_dir,
            upload_policy=settings.upload_policy,
            history_repository=history_repository,
        )
    except Exception:
        history_repository.close()
        raise
    host, port = server.server_address
    logger.info("UDM_10 TCP server đang lắng nghe tại %s:%s", host, port)
    logger.info("Thư mục lưu upload: %s", settings.upload_dir)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Đang dừng TCP server.")
    finally:
        server.server_close()
        history_repository.close()
    return 0
