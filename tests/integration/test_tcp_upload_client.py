from __future__ import annotations

import threading
from pathlib import Path

from udm10.client.transports.tcp_adapter import (
    ConflictNotice,
    TcpUploadClient,
    TransferProgress,
)
from udm10.client.models.upload import ConflictPolicy, UploadStatus
from udm10.config import TcpSettings, UploadPolicySettings
from udm10.server import create_server


def test_tcp_client_streams_file_and_reports_byte_based_progress(tmp_path: Path) -> None:
    source = tmp_path / "nguồn Unicode.bin"
    payload = bytes(range(251)) * 8
    source.write_bytes(payload)
    destination = tmp_path / "server"
    server_settings = TcpSettings(
        bind_host="127.0.0.1",
        client_host="127.0.0.1",
        port=0,
        max_control_message_bytes=4096,
        socket_timeout_seconds=2,
        file_chunk_size_bytes=97,
    )
    server = create_server(
        server_settings,
        upload_dir=destination,
        upload_policy=UploadPolicySettings(None, None, None),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        client = TcpUploadClient(
            host=host,
            port=port,
            timeout_seconds=2,
            max_control_message_bytes=4096,
            chunk_size_bytes=97,
            progress_interval_seconds=0,
        )
        progress: list[TransferProgress] = []

        outcome = client.upload(
            source,
            request_id="client-1",
            conflict=ConflictPolicy.RENAME,
            on_progress=progress.append,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)

    assert outcome.status == UploadStatus.COMPLETED
    assert outcome.stored_name == source.name
    assert (destination / source.name).read_bytes() == payload
    assert progress[-1].bytes_sent == len(payload)
    assert progress[-1].percent == 100
    assert all(item.speed_bytes_per_second >= 0 for item in progress)
    assert len(progress) > 2


def test_tc21_client_reports_server_conflict_without_sending_payload(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source = source_dir / "trùng tên.txt"
    source.write_bytes(b"client-payload")
    destination = tmp_path / "server"
    destination.mkdir()
    (destination / source.name).write_bytes(b"server-original")
    settings = TcpSettings(
        bind_host="127.0.0.1",
        client_host="127.0.0.1",
        port=0,
        max_control_message_bytes=4096,
        socket_timeout_seconds=2,
        file_chunk_size_bytes=97,
    )
    server = create_server(
        settings,
        upload_dir=destination,
        upload_policy=UploadPolicySettings(None, None, None),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    progress: list[TransferProgress] = []
    try:
        host, port = server.server_address
        client = TcpUploadClient(
            host=host,
            port=port,
            timeout_seconds=2,
            max_control_message_bytes=4096,
            chunk_size_bytes=97,
            progress_interval_seconds=0,
        )
        result = client.upload(
            source,
            request_id="duplicate-client",
            conflict=None,
            on_progress=progress.append,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)

    assert result == ConflictNotice(source.name)
    assert progress == []
    assert (destination / source.name).read_bytes() == b"server-original"


def test_tc10_large_file_is_streamed_in_chunks_with_monotonic_progress(
    tmp_path: Path,
) -> None:
    source = tmp_path / "tệp-lớn.pdf"
    source.write_bytes(b"UDM10" * (1024 * 1024))
    destination = tmp_path / "server-large"
    settings = TcpSettings(
        bind_host="127.0.0.1",
        client_host="127.0.0.1",
        port=0,
        max_control_message_bytes=4096,
        socket_timeout_seconds=5,
        file_chunk_size_bytes=64 * 1024,
    )
    server = create_server(
        settings,
        upload_dir=destination,
        upload_policy=UploadPolicySettings(None, 10, (".pdf",)),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    progress: list[TransferProgress] = []
    try:
        host, port = server.server_address
        client = TcpUploadClient(
            host=host,
            port=port,
            timeout_seconds=5,
            max_control_message_bytes=4096,
            chunk_size_bytes=64 * 1024,
            progress_interval_seconds=0,
        )
        outcome = client.upload(
            source,
            request_id="large-file",
            conflict=ConflictPolicy.RENAME,
            on_progress=progress.append,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)

    assert outcome.status == UploadStatus.COMPLETED
    assert (destination / source.name).stat().st_size == source.stat().st_size
    assert len(progress) > 32
    assert [item.bytes_sent for item in progress] == sorted(
        item.bytes_sent for item in progress
    )
    assert progress[-1].percent == 100
