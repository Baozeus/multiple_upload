from __future__ import annotations

from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "ui-handoff" / "client"))

from multiple_upload_client.config import ClientConfig
from multiple_upload_client.models import UploadStatus
from multiple_upload_client.queue_manager import UploadQueue


ENVIRONMENT_KEYS = {
    "UDM10_TRANSPORT",
    "UDM10_TCP_HOST",
    "UDM10_TCP_PORT",
    "UDM10_API_BASE_URL",
    "UDM10_UPLOAD_ENDPOINT",
    "UDM10_ALLOW_MOCK_FALLBACK",
    "UDM10_MAX_CONCURRENT",
    "UDM10_CONFLICT_POLICY",
}


class ConfigTests(unittest.TestCase):
    def _clean_environment(self):
        return patch.dict(
            os.environ,
            {key: "" for key in ENVIRONMENT_KEYS},
            clear=False,
        )

    def test_tcp_is_default_transport(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            with patch.dict(os.environ, {}, clear=True):
                config = ClientConfig.load(path)
        self.assertEqual(config.transport, "tcp")
        self.assertEqual((config.tcp_host, config.tcp_port), ("127.0.0.1", 9000))
        self.assertFalse(config.allow_mock_fallback)

    def test_http_adapter_keeps_legacy_url_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                '{"base_url":"http://127.0.0.1:8080/",'
                '"upload_endpoint":"/api/uploads"}',
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                config = ClientConfig.load(path)
        self.assertEqual(config.transport, "http")
        self.assertEqual(config.upload_url, "http://127.0.0.1:8080/api/uploads")


class QueueTests(unittest.TestCase):
    def test_fifo_limit_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid_paths = []
            for index in range(4):
                path = root / f"file-{index}.txt"
                path.write_text(str(index), encoding="utf-8")
                valid_paths.append(path)
            invalid = root / "archive.zip"
            invalid.write_bytes(b"zip")

            queue = UploadQueue(max_concurrent=2)
            added = queue.add_paths([*valid_paths, invalid])
            first_batch = queue.take_next()

            self.assertEqual([item.path for item in added], valid_paths)
            self.assertEqual([item.path for item in first_batch], valid_paths[:2])
            self.assertEqual(len(queue.rejected), 1)
            self.assertTrue(
                all(item.status is UploadStatus.UPLOADING for item in first_batch)
            )


if __name__ == "__main__":
    unittest.main()
