from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


CODE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_ROOT))

from protocol import MAX_UPLOAD_SIZE, validate_conflict_policy, validate_upload_header
from duplicate_handler import release_file, reserve_file_path
from upload_handler import save_incoming_file


class ProtocolValidationTests(unittest.TestCase):
    def test_accepts_supported_extension_at_exact_10_gb_limit(self) -> None:
        name, size = validate_upload_header(
            {"filename": "tai-lieu.pdf", "filesize": MAX_UPLOAD_SIZE}
        )
        self.assertEqual(name, "tai-lieu.pdf")
        self.assertEqual(size, MAX_UPLOAD_SIZE)

    def test_rejects_file_larger_than_10_gb(self) -> None:
        with self.assertRaisesRegex(ValueError, "max 10GB"):
            validate_upload_header(
                {"filename": "tai-lieu.pdf", "filesize": MAX_UPLOAD_SIZE + 1}
            )

    def test_rejects_unsupported_extension(self) -> None:
        with self.assertRaisesRegex(ValueError, "khong duoc ho tro"):
            validate_upload_header({"filename": "archive.zip", "filesize": 12})

    def test_old_client_defaults_to_rename(self) -> None:
        self.assertEqual(validate_conflict_policy({}), "rename")

    def test_rejects_unknown_conflict_policy(self) -> None:
        with self.assertRaisesRegex(ValueError, "conflict phai la"):
            validate_conflict_policy({"conflict": "ask"})


class StorageConflictTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.upload_dir = Path(self.temporary_directory.name)
        (self.upload_dir / "report.txt").write_bytes(b"original")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_rename_preserves_existing_file(self) -> None:
        result = save_incoming_file(
            str(self.upload_dir), "report.txt", [b"new"], conflict="rename"
        )
        self.assertEqual(result["final_name"], "report(1).txt")
        self.assertEqual((self.upload_dir / "report.txt").read_bytes(), b"original")
        self.assertEqual((self.upload_dir / "report(1).txt").read_bytes(), b"new")

    def test_overwrite_replaces_only_after_complete_write(self) -> None:
        result = save_incoming_file(
            str(self.upload_dir), "report.txt", [b"replacement"], conflict="overwrite"
        )
        self.assertTrue(result["completed"])
        self.assertEqual((self.upload_dir / "report.txt").read_bytes(), b"replacement")

    def test_skip_preserves_existing_file(self) -> None:
        result = save_incoming_file(
            str(self.upload_dir), "report.txt", [b"ignored"], conflict="skip"
        )
        self.assertTrue(result["skipped"])
        self.assertEqual((self.upload_dir / "report.txt").read_bytes(), b"original")

    def test_failed_stream_keeps_existing_file_and_cleans_part(self) -> None:
        def broken_stream():
            yield b"partial"
            raise ConnectionError("test interruption")

        with self.assertRaises(ConnectionError):
            save_incoming_file(
                str(self.upload_dir), "report.txt", broken_stream(), conflict="overwrite"
            )
        self.assertEqual((self.upload_dir / "report.txt").read_bytes(), b"original")
        self.assertEqual(list(self.upload_dir.glob("*.part")), [])

    def test_tempfile_failure_releases_reserved_destination(self) -> None:
        with patch("duplicate_handler.tempfile.mkstemp", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                reserve_file_path(str(self.upload_dir), "new.txt", "overwrite")

        reservation = reserve_file_path(str(self.upload_dir), "new.txt", "overwrite")
        self.assertIsNotNone(reservation)
        reservation["file"].close()
        Path(reservation["temporary_path"]).unlink()
        release_file(reservation)


if __name__ == "__main__":
    unittest.main()
