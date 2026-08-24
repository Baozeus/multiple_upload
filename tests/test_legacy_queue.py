from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Code"))

from codelogic import QuanlyUpload


class LegacyQueueTests(unittest.TestCase):
    def test_new_files_enter_fifo_queue_before_worker_assignment(self) -> None:
        manager = QuanlyUpload(so_file_toi_da=3)
        files = [{"name": f"file-{index}.txt"} for index in range(4)]

        for file_info in files:
            manager.add_file(file_info)

        self.assertEqual(list(manager.queue), files)
        self.assertEqual(manager.uploading, [])


if __name__ == "__main__":
    unittest.main()
