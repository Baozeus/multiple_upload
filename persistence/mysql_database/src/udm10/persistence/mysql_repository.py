"""MySQL 8 repository for upload metadata; file bytes remain on disk."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from udm10.config import MySqlSettings
from udm10.persistence.interfaces import (
    PersistenceError,
    PersistenceUnavailable,
    UploadBatchRecord,
    UploadEventRecord,
    UploadFileRecord,
)


class MySqlHistoryRepository:
    def __init__(
        self,
        settings: MySqlSettings,
        *,
        connect: Callable[..., Any] | None = None,
    ) -> None:
        self._settings = settings
        self._connect = connect or _default_connect
        self._connection: Any | None = None
        self._lock = threading.RLock()

    def initialize(self) -> None:
        connection: Any | None = None
        try:
            connection = self._connect(
                host=self._settings.host,
                port=self._settings.port,
                database=self._settings.database,
                user=self._settings.user,
                password=self._settings.password,
                connection_timeout=5,
                autocommit=False,
                charset="utf8mb4",
                use_unicode=True,
            )
            cursor = connection.cursor()
            try:
                for table in ("upload_batches", "upload_files", "upload_events"):
                    cursor.execute(f"SELECT 1 FROM `{table}` LIMIT 1")
                    cursor.fetchone()
            finally:
                cursor.close()
        except Exception as exc:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
            self._connection = None
            endpoint = (
                f"{self._settings.host}:{self._settings.port}/"
                f"{self._settings.database}"
            )
            raise PersistenceUnavailable(
                f"Không thể kết nối hoặc kiểm tra schema MySQL tại {endpoint}. "
                "Hãy kiểm tra cấu hình và chạy migration."
            ) from exc
        self._connection = connection

    def save_batch(self, batch: UploadBatchRecord) -> None:
        self._execute(
            """
            INSERT INTO upload_batches (id, started_at, completed_at)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                started_at = LEAST(started_at, VALUES(started_at)),
                completed_at = CASE
                    WHEN VALUES(completed_at) IS NULL THEN completed_at
                    WHEN completed_at IS NULL THEN VALUES(completed_at)
                    ELSE GREATEST(completed_at, VALUES(completed_at))
                END
            """,
            (batch.id, _to_mysql_time(batch.started_at), _to_mysql_time(batch.completed_at)),
        )

    def save_file(self, file: UploadFileRecord) -> None:
        self._execute(
            """
            INSERT INTO upload_files (
                id, batch_id, original_name, stored_name, size_bytes, status,
                duplicate_policy, error_message, started_at, completed_at,
                relative_path
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                batch_id = VALUES(batch_id),
                original_name = VALUES(original_name),
                stored_name = VALUES(stored_name),
                size_bytes = VALUES(size_bytes),
                status = VALUES(status),
                duplicate_policy = VALUES(duplicate_policy),
                error_message = VALUES(error_message),
                started_at = VALUES(started_at),
                completed_at = VALUES(completed_at),
                relative_path = VALUES(relative_path)
            """,
            (
                file.id,
                file.batch_id,
                file.original_name,
                file.stored_name,
                file.size_bytes,
                file.status,
                file.duplicate_policy,
                file.error_message,
                _to_mysql_time(file.started_at),
                _to_mysql_time(file.completed_at),
                file.relative_path,
            ),
        )

    def append_event(self, event: UploadEventRecord) -> None:
        self._execute(
            """
            INSERT INTO upload_events (id, file_id, status, message, created_at)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                status = VALUES(status),
                message = VALUES(message),
                created_at = VALUES(created_at)
            """,
            (
                event.id,
                event.file_id,
                event.status,
                event.message,
                _to_mysql_time(event.created_at),
            ),
        )

    def list_batches(self) -> tuple[UploadBatchRecord, ...]:
        rows = self._query(
            "SELECT id, started_at, completed_at FROM upload_batches "
            "ORDER BY started_at DESC"
        )
        return tuple(
            UploadBatchRecord(row[0], _from_mysql_time(row[1]), _from_mysql_time(row[2]))
            for row in rows
        )

    def list_files(self) -> tuple[UploadFileRecord, ...]:
        rows = self._query(
            """
            SELECT id, batch_id, original_name, stored_name, size_bytes, status,
                   duplicate_policy, error_message, started_at, completed_at,
                   relative_path
            FROM upload_files
            ORDER BY COALESCE(completed_at, started_at) DESC
            """
        )
        return tuple(
            UploadFileRecord(
                id=row[0],
                batch_id=row[1],
                original_name=row[2],
                stored_name=row[3],
                size_bytes=row[4],
                status=row[5],
                duplicate_policy=row[6],
                error_message=row[7],
                started_at=_from_mysql_time(row[8]),
                completed_at=_from_mysql_time(row[9]),
                relative_path=row[10],
            )
            for row in rows
        )

    def list_events(
        self, file_id: str | None = None
    ) -> tuple[UploadEventRecord, ...]:
        sql = "SELECT id, file_id, status, message, created_at FROM upload_events"
        parameters: tuple[Any, ...] = ()
        if file_id is not None:
            sql += " WHERE file_id = %s"
            parameters = (file_id,)
        sql += " ORDER BY created_at"
        return tuple(
            UploadEventRecord(row[0], row[1], row[2], row[3], _from_mysql_time(row[4]))
            for row in self._query(sql, parameters)
        )

    def close(self) -> None:
        with self._lock:
            connection, self._connection = self._connection, None
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass

    def _execute(self, sql: str, parameters: tuple[Any, ...]) -> None:
        with self._lock:
            connection = self._require_connection()
            cursor = connection.cursor()
            try:
                cursor.execute(sql, parameters)
                connection.commit()
            except Exception as exc:
                try:
                    connection.rollback()
                except Exception:
                    pass
                raise PersistenceError("Không thể ghi lịch sử vào MySQL.") from exc
            finally:
                cursor.close()

    def _query(
        self, sql: str, parameters: tuple[Any, ...] = ()
    ) -> tuple[tuple[Any, ...], ...]:
        with self._lock:
            connection = self._require_connection()
            cursor = connection.cursor()
            try:
                cursor.execute(sql, parameters)
                return tuple(cursor.fetchall())
            except Exception as exc:
                raise PersistenceError("Không thể đọc lịch sử từ MySQL.") from exc
            finally:
                cursor.close()

    def _require_connection(self) -> Any:
        if self._connection is None:
            raise PersistenceUnavailable("Kết nối MySQL chưa được khởi tạo.")
        return self._connection


def _default_connect(**kwargs: Any) -> Any:
    import mysql.connector

    return mysql.connector.connect(**kwargs)


def _to_mysql_time(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _from_mysql_time(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value
