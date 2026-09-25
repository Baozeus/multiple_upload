"""Persistence contracts and the optional MySQL implementation."""

from .interfaces import (
    PersistenceError,
    PersistenceUnavailable,
    UploadBatchRecord,
    UploadEventRecord,
    UploadFileRecord,
)
from .mysql_repository import MySqlHistoryRepository

__all__ = [
    "MySqlHistoryRepository",
    "PersistenceError",
    "PersistenceUnavailable",
    "UploadBatchRecord",
    "UploadEventRecord",
    "UploadFileRecord",
]
