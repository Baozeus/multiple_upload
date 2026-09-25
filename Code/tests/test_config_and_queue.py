from __future__ import annotations

from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch


CODE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_ROOT / "ui-handoff" / "client"))

from multiple_upload_client.config import ClientConfig
from multiple_upload_client.models import UploadStatus
from multiple_upload_client.queue_manager import (
    MAX_CONCURRENT_UPLOADS,
    MAX_FILES_PER_SELECTION,
    MAX_UPLOAD_SIZE,
    UploadQueue,
)


ENVIRONMENT_KEYS = {
    "UDM10_TRANSPORT",
    "UDM10_TCP_HOST",
    "UDM10_TCP_PORT",
    "UDM10_API_BASE_URL",
    "UDM10_UPLOAD_ENDPOINT",
    "UDM10_ALLOW_MOCK_FALLBACK",
    "UDM10_MAX_CONCURRENT",
    "UDM10_MAX_UPLOAD_SIZE",
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

    def test_confirmed_defaults_are_three_uploads_and_500_kib(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            with patch.dict(os.environ, {}, clear=True):
                config = ClientConfig.load(path)

        self.assertEqual(MAX_FILES_PER_SELECTION, 6)
        self.assertEqual(MAX_CONCURRENT_UPLOADS, 3)
        self.assertEqual(MAX_UPLOAD_SIZE, 512_000)
        self.assertEqual(config.max_concurrent, 3)
        self.assertEqual(config.max_upload_size, 512_000)

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

    def test_tcp_host_port_and_size_limit_are_configurable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                '{"transport":"tcp","tcp_host":"localhost","tcp_port":19123,'
                '"max_upload_size":512000}',
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                config = ClientConfig.load(path)
        self.assertEqual((config.tcp_host, config.tcp_port), ("localhost", 19123))
        self.assertEqual(config.max_upload_size, 512000)

    def test_config_cannot_raise_confirmed_500_kib_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                '{"transport":"tcp","max_upload_size":512001}',
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(ValueError, "512.000"):
                    ClientConfig.load(path)


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

    def test_accepts_at_most_six_files_per_selection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for index in range(8):
                path = root / f"selected-{index}.txt"
                path.write_text(str(index), encoding="utf-8")
                paths.append(path)
            queue = UploadQueue(max_concurrent=3)
            added = queue.add_paths(paths)
        self.assertEqual([item.path.name for item in added], [p.name for p in paths[:6]])
        self.assertEqual(len(queue.rejected), 2)
        self.assertTrue(all("tối đa 6" in reason for _, reason in queue.rejected))

    def test_rejected_overflow_never_enters_queue_and_can_be_added_next_time(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for index in range(8):
                path = root / f"batch-{index}.txt"
                path.write_text(str(index), encoding="utf-8")
                paths.append(path)

            queue = UploadQueue(max_concurrent=3)
            first_admission = queue.add_paths(paths)
            self.assertEqual(
                [item.path for item in first_admission],
                paths[:6],
            )
            self.assertEqual(
                [path for path, _reason in queue.rejected],
                paths[6:],
            )
            self.assertEqual(
                [item.path for item in queue.items.values()],
                paths[:6],
            )

            second_admission = queue.add_paths(paths[6:])
            self.assertEqual(
                [item.path for item in second_admission],
                paths[6:],
            )
            self.assertEqual(len(queue.items), 8)

    def test_invalid_files_do_not_consume_the_six_valid_file_quota(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invalid = root / "invalid.exe"
            invalid.write_bytes(b"invalid")
            valid = []
            for index in range(6):
                path = root / f"valid-{index}.txt"
                path.write_text(str(index), encoding="utf-8")
                valid.append(path)

            queue = UploadQueue(max_concurrent=3)
            added = queue.add_paths([invalid, *valid])

        self.assertEqual([item.path.name for item in added], [path.name for path in valid])
        self.assertEqual(queue.rejected[0][0].name, "invalid.exe")

    def test_configured_size_limit_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "over-limit.txt"
            path.write_bytes(b"x" * (500 * 1024 + 1))
            queue = UploadQueue(max_concurrent=3, max_upload_size=500 * 1024)
            self.assertEqual(queue.add_paths([path]), [])
            self.assertIn("giới hạn cấu hình", queue.rejected[0][1])

    def test_six_files_complete_in_two_fifo_waves_of_three(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for index in range(6):
                path = root / f"fifo-{index}.txt"
                path.write_text(str(index), encoding="utf-8")
                paths.append(path)
            queue = UploadQueue(max_concurrent=3)
            queue.add_paths(paths)
            first = queue.take_next()
            self.assertEqual([item.path for item in first], paths[:3])
            for item in first:
                item.status = UploadStatus.COMPLETED
            second = queue.take_next()
            self.assertEqual([item.path for item in second], paths[3:])


if __name__ == "__main__":
    unittest.main()
