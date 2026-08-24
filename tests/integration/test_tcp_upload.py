from __future__ import annotations

import socket
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from udm10.config import TcpSettings, UploadPolicySettings
from udm10.protocol import receive_message, send_message
from udm10.server import create_server


@contextmanager
def running_server(
    upload_dir: Path,
    *,
    socket_timeout: float = 2.0,
    chunk_size: int = 64 * 1024,
):
    settings = TcpSettings(
        bind_host="127.0.0.1",
        client_host="127.0.0.1",
        port=0,
        max_control_message_bytes=4096,
        socket_timeout_seconds=socket_timeout,
        file_chunk_size_bytes=chunk_size,
    )
    policy = UploadPolicySettings(
        max_concurrent_uploads=None,
        max_file_size_mb=None,
        allowed_extensions=None,
    )
    server = create_server(settings, upload_dir=upload_dir, upload_policy=policy)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


def test_uploads_one_binary_file_over_tcp(tmp_path: Path) -> None:
    payload = b"UDM-10\x00binary\xffpayload"
    with running_server(tmp_path) as server:
        with socket.create_connection(server.server_address, timeout=2) as connection:
            send_message(
                connection,
                {
                    "type": "upload.start",
                    "request_id": "file-1",
                    "filename": "bao-cao.bin",
                    "size": len(payload),
                    "conflict": "rename",
                },
            )
            ready = receive_message(connection)
            assert ready == {"type": "upload.ready", "request_id": "file-1"}
            connection.sendall(payload)
            result = receive_message(connection)

    assert result == {
        "type": "upload.result",
        "request_id": "file-1",
        "status": "completed",
        "filename": "bao-cao.bin",
        "bytes_received": len(payload),
    }
    assert (tmp_path / "bao-cao.bin").read_bytes() == payload


def test_tc23_server_requests_a_choice_then_overwrites_the_exact_target(
    tmp_path: Path,
) -> None:
    target = tmp_path / "báo cáo.txt"
    target.write_bytes(b"old")
    payload = "nội dung mới".encode()

    with running_server(tmp_path) as server:
        with socket.create_connection(server.server_address, timeout=2) as connection:
            send_message(
                connection,
                {
                    "type": "upload.start",
                    "request_id": "conflict-check",
                    "filename": target.name,
                    "size": len(payload),
                },
            )
            conflict = receive_message(connection)

        with socket.create_connection(server.server_address, timeout=2) as connection:
            send_message(
                connection,
                {
                    "type": "upload.start",
                    "request_id": "overwrite-choice",
                    "filename": target.name,
                    "size": len(payload),
                    "conflict": "overwrite",
                },
            )
            assert receive_message(connection) == {
                "type": "upload.ready",
                "request_id": "overwrite-choice",
            }
            connection.sendall(payload)
            result = receive_message(connection)

    assert conflict == {
        "type": "upload.conflict",
        "request_id": "conflict-check",
        "filename": target.name,
    }
    assert result["status"] == "completed"
    assert result["filename"] == target.name
    assert target.read_bytes() == payload
    assert not (tmp_path / "báo cáo_1.txt").exists()


def test_tc24_rename_preserves_original_and_creates_a_unique_name(tmp_path: Path) -> None:
    target = tmp_path / "dữ liệu.csv"
    target.write_bytes(b"original")

    with running_server(tmp_path) as server:
        with socket.create_connection(server.server_address, timeout=2) as connection:
            result = _upload(
                connection,
                "rename-choice",
                target.name,
                b"new-copy",
                conflict="rename",
            )

    assert result["status"] == "completed"
    assert result["filename"] == "dữ liệu_1.csv"
    assert target.read_bytes() == b"original"
    assert (tmp_path / "dữ liệu_1.csv").read_bytes() == b"new-copy"


def test_tc25_skip_returns_without_accepting_payload_or_changing_the_file(
    tmp_path: Path,
) -> None:
    target = tmp_path / "đã có.txt"
    target.write_bytes(b"keep-me")

    with running_server(tmp_path) as server:
        with socket.create_connection(server.server_address, timeout=2) as connection:
            send_message(
                connection,
                {
                    "type": "upload.start",
                    "request_id": "skip-choice",
                    "filename": target.name,
                    "size": 999_999,
                    "conflict": "skip",
                },
            )
            result = receive_message(connection)

    assert result == {
        "type": "upload.result",
        "request_id": "skip-choice",
        "status": "skipped",
        "filename": target.name,
        "bytes_received": 0,
    }
    assert target.read_bytes() == b"keep-me"
    assert list(tmp_path.iterdir()) == [target]


def test_tc26_concurrent_same_name_is_reserved_before_payload(tmp_path: Path) -> None:
    payload = b"first-writer"
    with running_server(tmp_path) as server:
        first = socket.create_connection(server.server_address, timeout=2)
        second = socket.create_connection(server.server_address, timeout=2)
        try:
            start = {
                "type": "upload.start",
                "filename": "cùng tên.bin",
                "size": len(payload),
            }
            send_message(first, {**start, "request_id": "race-first"})
            assert receive_message(first) == {
                "type": "upload.ready",
                "request_id": "race-first",
            }

            send_message(second, {**start, "request_id": "race-second"})
            conflict = receive_message(second)

            first.sendall(payload)
            completed = receive_message(first)
        finally:
            first.close()
            second.close()

    assert conflict == {
        "type": "upload.conflict",
        "request_id": "race-second",
        "filename": "cùng tên.bin",
    }
    assert completed["status"] == "completed"
    assert (tmp_path / "cùng tên.bin").read_bytes() == payload
    assert [path.name for path in tmp_path.iterdir()] == ["cùng tên.bin"]


def test_tc26_concurrent_rename_choices_receive_distinct_destinations(
    tmp_path: Path,
) -> None:
    original = tmp_path / "song song.txt"
    original.write_bytes(b"original")
    with running_server(tmp_path) as server:
        first = socket.create_connection(server.server_address, timeout=2)
        second = socket.create_connection(server.server_address, timeout=2)
        try:
            for connection, request_id in (
                (first, "rename-race-1"),
                (second, "rename-race-2"),
            ):
                send_message(
                    connection,
                    {
                        "type": "upload.start",
                        "request_id": request_id,
                        "filename": original.name,
                        "size": 1,
                        "conflict": "rename",
                    },
                )
                assert receive_message(connection) == {
                    "type": "upload.ready",
                    "request_id": request_id,
                }
            first.sendall(b"1")
            second.sendall(b"2")
            results = [receive_message(first), receive_message(second)]
        finally:
            first.close()
            second.close()

    assert {result["filename"] for result in results} == {
        "song song_1.txt",
        "song song_2.txt",
    }
    assert original.read_bytes() == b"original"
    assert {path.read_bytes() for path in tmp_path.glob("song song_*.txt")} == {
        b"1",
        b"2",
    }


def test_rejects_windows_unsafe_filename_without_accepting_payload(tmp_path: Path) -> None:
    with running_server(tmp_path) as server:
        with socket.create_connection(server.server_address, timeout=2) as connection:
            send_message(
                connection,
                {
                    "type": "upload.start",
                    "request_id": "unsafe-1",
                    "filename": "bao?cao.txt",
                    "size": 4,
                    "conflict": "rename",
                },
            )
            result = receive_message(connection)

    assert result["type"] == "upload.result"
    assert result["request_id"] == "unsafe-1"
    assert result["status"] == "failed"
    assert result["code"] == "invalid_filename"
    assert list(tmp_path.iterdir()) == []


def test_uploads_multiple_unicode_files_on_one_connection(tmp_path: Path) -> None:
    uploads = [
        ("unicode-1", "dữ liệu 测试.txt", "Xin chào".encode()),
        ("unicode-2", "ảnh Đà Nẵng.bin", bytes(range(64))),
    ]
    with running_server(tmp_path, chunk_size=7) as server:
        with socket.create_connection(server.server_address, timeout=2) as connection:
            results = [
                _upload(connection, request_id, filename, payload)
                for request_id, filename, payload in uploads
            ]

    assert [result["status"] for result in results] == ["completed", "completed"]
    for _request_id, filename, payload in uploads:
        assert (tmp_path / filename).read_bytes() == payload


def test_accepts_zero_byte_file(tmp_path: Path) -> None:
    with running_server(tmp_path) as server:
        with socket.create_connection(server.server_address, timeout=2) as connection:
            result = _upload(connection, "empty-1", "rỗng.txt", b"")

    assert result["status"] == "completed"
    assert result["bytes_received"] == 0
    assert (tmp_path / "rỗng.txt").read_bytes() == b""


def test_reports_missing_payload_and_removes_partial_file(tmp_path: Path) -> None:
    with running_server(tmp_path) as server:
        with socket.create_connection(server.server_address, timeout=2) as connection:
            send_message(
                connection,
                {
                    "type": "upload.start",
                    "request_id": "short-1",
                    "filename": "thieu.bin",
                    "size": 10,
                    "conflict": "rename",
                },
            )
            assert receive_message(connection)["type"] == "upload.ready"
            connection.sendall(b"1234")
            connection.shutdown(socket.SHUT_WR)
            result = receive_message(connection)

    assert result["status"] == "failed"
    assert result["code"] == "incomplete_payload"
    assert result["bytes_received"] == 4
    assert list(tmp_path.iterdir()) == []


def test_times_out_stalled_payload_with_clear_error(tmp_path: Path) -> None:
    with running_server(tmp_path, socket_timeout=0.15) as server:
        with socket.create_connection(server.server_address, timeout=2) as connection:
            send_message(
                connection,
                {
                    "type": "upload.start",
                    "request_id": "timeout-1",
                    "filename": "cham.bin",
                    "size": 10,
                    "conflict": "rename",
                },
            )
            assert receive_message(connection)["type"] == "upload.ready"
            result = receive_message(connection)

    assert result["status"] == "failed"
    assert result["code"] == "transfer_timeout"
    assert "thời gian" in result["message"].casefold()
    assert list(tmp_path.iterdir()) == []


def test_disconnect_cleans_partial_and_server_accepts_next_connection(tmp_path: Path) -> None:
    with running_server(tmp_path) as server:
        connection = socket.create_connection(server.server_address, timeout=2)
        send_message(
            connection,
            {
                "type": "upload.start",
                "request_id": "drop-1",
                "filename": "dang-do.bin",
                "size": 100,
                "conflict": "rename",
            },
        )
        assert receive_message(connection)["type"] == "upload.ready"
        connection.sendall(b"partial")
        connection.close()
        _wait_until(lambda: not any(tmp_path.iterdir()))

        with socket.create_connection(server.server_address, timeout=2) as next_connection:
            result = _upload(next_connection, "after-drop", "sau-ngat.txt", b"ok")

    assert result["status"] == "completed"
    assert (tmp_path / "sau-ngat.txt").read_bytes() == b"ok"


def test_rejected_file_does_not_block_next_file_on_same_connection(tmp_path: Path) -> None:
    with running_server(tmp_path) as server:
        with socket.create_connection(server.server_address, timeout=2) as connection:
            send_message(
                connection,
                {
                    "type": "upload.start",
                    "request_id": "bad-1",
                    "filename": "../outside.txt",
                    "size": 3,
                    "conflict": "rename",
                },
            )
            failed = receive_message(connection)
            completed = _upload(connection, "good-1", "hop-le.txt", b"yes")

    assert failed["status"] == "failed"
    assert failed["code"] == "invalid_filename"
    assert completed["status"] == "completed"
    assert (tmp_path / "hop-le.txt").read_bytes() == b"yes"


def _upload(
    connection: socket.socket,
    request_id: str,
    filename: str,
    payload: bytes,
    *,
    conflict: str = "rename",
) -> dict:
    send_message(
        connection,
        {
            "type": "upload.start",
            "request_id": request_id,
            "filename": filename,
            "size": len(payload),
            "conflict": conflict,
        },
    )
    ready = receive_message(connection)
    assert ready == {"type": "upload.ready", "request_id": request_id}
    if payload:
        connection.sendall(payload)
    return receive_message(connection)


def _wait_until(predicate, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Điều kiện không đạt trước timeout.")
