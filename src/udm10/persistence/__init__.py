"""History persistence public interface."""

from collections.abc import Callable
from typing import Any

from udm10.config import HistorySettings

from udm10.persistence.interfaces import (
    HistoryRepository,
    PersistenceError,
    PersistenceUnavailable,
    UploadBatchRecord,
    UploadEventRecord,
    UploadFileRecord,
)
from udm10.persistence.json_repository import JsonHistoryRepository
from udm10.persistence.mysql_repository import MySqlHistoryRepository


def create_history_repository(
    settings: HistorySettings,
    *,
    mysql_connect: Callable[..., Any] | None = None,
) -> HistoryRepository:
    """Create and verify the selected backend before the server starts."""
    if settings.backend == "mysql":
        repository = MySqlHistoryRepository(settings.mysql, connect=mysql_connect)
    elif settings.backend == "json":
        repository = JsonHistoryRepository(settings.json_path)
    else:
        raise PersistenceError(f"History backend không được hỗ trợ: {settings.backend}")
    repository.initialize()
    return repository


__all__ = [
    "HistoryRepository",
    "JsonHistoryRepository",
    "MySqlHistoryRepository",
    "PersistenceError",
    "PersistenceUnavailable",
    "UploadBatchRecord",
    "UploadEventRecord",
    "UploadFileRecord",
    "create_history_repository",
]
