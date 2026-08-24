from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import socket
import threading

import pytest

from udm10.persistence.interfaces import (
    UploadBatchRecord,
    UploadEventRecord,
    UploadFileRecord,
)
from udm10.persistence.json_repository import JsonHistoryRepository
from udm10.config import HistorySettings, MySqlSettings
from udm10.config import load_settings
from udm10.persistence import PersistenceUnavailable, create_history_repository
from udm10.config import TcpSettings, UploadPolicySettings
from udm10.protocol import receive_message, send_message
from udm10.server import create_server
from udm10.client.transports import TcpUploadClient
from udm10.client.models.history import HistoryResult


def test_tc27_json_history_survives_repository_restart_with_full_metadata(
    tmp_path: Path,
) -> None:
    history_path = tmp_path / "nested" / "history.json"
    started = datetime(2026, 8, 24, 8, 30, tzinfo=UTC)
    completed = datetime(2026, 8, 24, 8, 31, tzinfo=UTC)
    batch = UploadBatchRecord("batch-27", started, completed)
    file_record = UploadFileRecord(
        id="file-27",
        batch_id=batch.id,
        original_name="báo cáo Unicode.pdf",
        stored_name="báo cáo Unicode_1.pdf",
        size_bytes=1_234_567,
        status="completed",
        duplicate_policy="rename",
        error_message=None,
        started_at=started,
        completed_at=completed,
        relative_path="báo cáo Unicode_1.pdf",
    )
    event = UploadEventRecord(
        id="event-27",
        file_id=file_record.id,
        status="completed",
        message=None,
        created_at=completed,
    )

    writer = JsonHistoryRepository(history_path)
    writer.initialize()
    writer.save_batch(batch)
    writer.save_file(file_record)
    writer.append_event(event)
    writer.close()

    reader = JsonHistoryRepository(history_path)
    reader.initialize()
    assert reader.list_files() == (file_record,)
    assert reader.list_batches() == (batch,)
    assert reader.list_events(file_record.id) == (event,)
    reader.close()


def test_tc27_mysql_disabled_selects_json_fallback(tmp_path: Path) -> None:
    settings = load_settings(
        {
            "MYSQL_ENABLED": "false",
            "HISTORY_JSON_PATH": str(tmp_path / "fallback.json"),
        }
    )
    repository = create_history_repository(settings.history)
    try:
        assert isinstance(repository, JsonHistoryRepository)
        assert settings.history.json_path.exists()
    finally:
        repository.close()


def test_tc28_enabled_mysql_fails_fast_with_a_clear_secret_safe_error(
    tmp_path: Path,
) -> None:
    assert load_settings({}).history.mysql.database == "udm_10"
    settings = HistorySettings(
        backend="mysql",
        json_path=tmp_path / "unused.json",
        mysql=MySqlSettings(
            enabled=True,
            host="db.internal",
            port=3306,
            database="udm_10",
            user="udm_app",
            password="do-not-leak",
        ),
    )

    def unavailable_connector(**_kwargs):
        raise RuntimeError("connection refused for do-not-leak")

    with pytest.raises(PersistenceUnavailable) as captured:
        create_history_repository(settings, mysql_connect=unavailable_connector)

    message = str(captured.value)
    assert "MySQL" in message
    assert "db.internal:3306/udm_10" in message
    assert "do-not-leak" not in message


def test_tc28_server_does_not_bind_when_enabled_mysql_is_unavailable(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    from udm10.server import application

    settings = load_settings(
        {
            "MYSQL_ENABLED": "true",
            "MYSQL_DATABASE": "udm_10",
            "MYSQL_USER": "udm_app",
            "MYSQL_PASSWORD": "secret",
            "LOG_DIR": str(tmp_path / "logs"),
        }
    )
    server_created: list[bool] = []
    monkeypatch.setattr(application, "load_settings", lambda: settings)
    monkeypatch.setattr(
        application,
        "create_history_repository",
        lambda _settings: (_ for _ in ()).throw(
            PersistenceUnavailable("Không thể kết nối MySQL tại test-host.")
        ),
        raising=False,
    )
    monkeypatch.setattr(
        application,
        "create_server",
        lambda *_args, **_kwargs: server_created.append(True),
    )

    assert application.main() == 2
    assert server_created == []
    assert "Không thể kết nối MySQL" in capsys.readouterr().err


def test_tc28_mysql_repository_verifies_all_tables_without_real_database(
    tmp_path: Path,
) -> None:
    executed: list[str] = []
    connect_kwargs: dict = {}

    class Cursor:
        def execute(self, sql, _parameters=()):
            executed.append(" ".join(sql.split()))

        def fetchone(self):
            return (1,)

        def close(self):
            return None

    class Connection:
        closed = False

        def cursor(self):
            return Cursor()

        def close(self):
            self.closed = True

    connection = Connection()

    def connect(**kwargs):
        connect_kwargs.update(kwargs)
        return connection

    settings = HistorySettings(
        backend="mysql",
        json_path=tmp_path / "unused.json",
        mysql=MySqlSettings(True, "127.0.0.1", 3306, "udm_10", "app", "secret"),
    )
    repository = create_history_repository(settings, mysql_connect=connect)

    assert connect_kwargs["database"] == "udm_10"
    assert connect_kwargs["charset"] == "utf8mb4"
    assert [sql.split("`")[1] for sql in executed] == [
        "upload_batches",
        "upload_files",
        "upload_events",
    ]
    repository.close()
    assert connection.closed is True


def test_tc29_tcp_upload_records_batch_file_metadata_and_events(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    repository = JsonHistoryRepository(tmp_path / "history.json")
    repository.initialize()
    settings = TcpSettings(
        bind_host="127.0.0.1",
        client_host="127.0.0.1",
        port=0,
        max_control_message_bytes=4096,
        socket_timeout_seconds=2,
        file_chunk_size_bytes=7,
    )
    server = create_server(
        settings,
        upload_dir=upload_dir,
        upload_policy=UploadPolicySettings(None, None, None),
        history_repository=repository,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    payload = "nội dung lịch sử".encode()
    try:
        with socket.create_connection(server.server_address, timeout=2) as connection:
            send_message(
                connection,
                {
                    "type": "upload.start",
                    "request_id": "file-29",
                    "batch_id": "batch-29",
                    "filename": "báo cáo.txt",
                    "size": len(payload),
                },
            )
            assert receive_message(connection)["type"] == "upload.ready"
            connection.sendall(payload)
            assert receive_message(connection)["status"] == "completed"
        history_client = TcpUploadClient(
            host=server.server_address[0],
            port=server.server_address[1],
            timeout_seconds=2,
            max_control_message_bytes=4096,
            chunk_size_bytes=7,
        )
        history_entries = history_client.load_history()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)

    (record,) = repository.list_files()
    assert record.id == "file-29"
    assert record.batch_id == "batch-29"
    assert record.original_name == "báo cáo.txt"
    assert record.stored_name == "báo cáo.txt"
    assert record.size_bytes == len(payload)
    assert record.status == "completed"
    assert record.duplicate_policy is None
    assert record.error_message is None
    assert record.started_at <= record.completed_at
    assert record.relative_path == "báo cáo.txt"
    assert repository.list_batches()[0].id == "batch-29"
    assert [event.status for event in repository.list_events("file-29")] == [
        "uploading",
        "completed",
    ]
    assert (upload_dir / "báo cáo.txt").read_bytes() == payload
    assert not any(path.suffix == ".bin" for path in tmp_path.iterdir())
    assert len(history_entries) == 1
    assert history_entries[0].name == "báo cáo.txt"
    assert history_entries[0].result == HistoryResult.SUCCESS


def test_tc29_skip_persists_metadata_without_sending_file_payload(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    target = upload_dir / "đã có.txt"
    target.write_bytes(b"original")
    repository = JsonHistoryRepository(tmp_path / "history.json")
    repository.initialize()
    settings = TcpSettings("127.0.0.1", "127.0.0.1", 0, 4096, 2, 64)
    server = create_server(
        settings,
        upload_dir=upload_dir,
        upload_policy=UploadPolicySettings(None, None, None),
        history_repository=repository,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = TcpUploadClient(
            host=server.server_address[0],
            port=server.server_address[1],
            timeout_seconds=2,
            max_control_message_bytes=4096,
            chunk_size_bytes=64,
        )
        client.record_skip(
            request_id="skip-29",
            batch_id="batch-skip-29",
            batch_total=1,
            filename=target.name,
            size_bytes=999_999,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)

    (record,) = repository.list_files()
    assert record.status == "skipped"
    assert record.duplicate_policy == "skip"
    assert record.stored_name == target.name
    assert record.relative_path is None
    assert repository.list_events(record.id)[-1].status == "skipped"
    assert target.read_bytes() == b"original"
    assert list(upload_dir.iterdir()) == [target]
