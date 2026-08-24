
from pathlib import Path

from udm10.persistence.mysql_repository import MySqlHistoryRepository


def test_mysql_adapter_imports_and_migration_is_non_destructive():
    assert MySqlHistoryRepository.__name__ == "MySqlHistoryRepository"
    sql = (Path(__file__).parents[1] / "database/migrations/001_create_upload_history.sql").read_text(encoding="utf-8")
    executable = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--")).upper()
    assert " BLOB" not in executable
    assert "DROP " not in executable
    assert "TRUNCATE" not in executable
    assert "DELETE FROM" not in executable
