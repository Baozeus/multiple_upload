from __future__ import annotations

import threading
from pathlib import Path

from udm10.client.models.tcp_provider import TcpUploadProvider
from udm10.client.models.upload import UploadStatus
from udm10.client.transports import TcpUploadClient
from udm10.config import TcpSettings, UploadPolicySettings
from udm10.server import create_server
from udm10.persistence import JsonHistoryRepository


def test_tc29_qt_batch_persists_as_one_complete_batch(qtbot, tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    paths = []
    for index in range(3):
        path = source_dir / f"tệp-{index}.bin"
        path.write_bytes(bytes([index + 1]) * 4096)
        paths.append(path)

    destination = tmp_path / "server"
    settings = TcpSettings(
        bind_host="127.0.0.1",
        client_host="127.0.0.1",
        port=0,
        max_control_message_bytes=4096,
        socket_timeout_seconds=2,
        file_chunk_size_bytes=257,
    )
    repository = JsonHistoryRepository(tmp_path / "history.json")
    repository.initialize()
    server = create_server(
        settings,
        upload_dir=destination,
        upload_policy=UploadPolicySettings(None, None, None),
        history_repository=repository,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    provider = TcpUploadProvider(
        max_concurrent=2,
        uploader=TcpUploadClient(
            host=host,
            port=port,
            timeout_seconds=2,
            max_control_message_bytes=4096,
            chunk_size_bytes=257,
            progress_interval_seconds=0,
        ),
    )
    try:
        provider.add_files(paths)
        qtbot.waitUntil(
            lambda: len(provider.current_uploads()) == 3
            and all(
                item.status == UploadStatus.COMPLETED
                for item in provider.current_uploads()
            ),
            timeout=5000,
        )
    finally:
        provider.shutdown()
        server.shutdown()
        server.server_close()
        thread.join(2)

    for path in paths:
        assert (destination / path.name).read_bytes() == path.read_bytes()
    files = repository.list_files()
    batches = repository.list_batches()
    assert len(files) == 3
    assert len({file.batch_id for file in files}) == 1
    assert len(batches) == 1
    assert batches[0].completed_at is not None
    assert batches[0].started_at <= min(file.started_at for file in files)
    assert batches[0].completed_at >= max(file.completed_at for file in files)
