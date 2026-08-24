"""Local, client-owned upload history.

The current server does not expose a history endpoint. This store keeps real
terminal upload outcomes on the current machine and never inserts mock rows.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
from pathlib import Path

from .models import UploadItem, UploadStatus


def default_history_path() -> Path:
    override = os.getenv("UDM10_HISTORY_FILE")
    if override:
        return Path(override).expanduser()
    local_app_data = os.getenv("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / ".local" / "share"
    return base / "UDM_10" / "upload_history.json"


@dataclass(frozen=True, slots=True)
class HistoryRecord:
    id: str
    name: str
    file_type: str
    size: int
    uploaded_at: str
    status: str
    conflict_result: str
    source: str

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "HistoryRecord":
        return cls(
            id=str(value.get("id", "")),
            name=str(value.get("name", "")),
            file_type=str(value.get("file_type", "TỆP")),
            size=int(value.get("size", 0)),
            uploaded_at=str(value.get("uploaded_at", "")),
            status=str(value.get("status", UploadStatus.ERROR.value)),
            conflict_result=str(value.get("conflict_result", "Không")),
            source=str(value.get("source", "Client")),
        )

    @property
    def uploaded_at_display(self) -> str:
        try:
            parsed = datetime.fromisoformat(self.uploaded_at)
            return parsed.strftime("%d/%m/%Y  %H:%M")
        except ValueError:
            return self.uploaded_at or "—"


class HistoryStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_history_path()

    def list_records(self) -> list[HistoryRecord]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(raw, list):
            return []
        records = [HistoryRecord.from_dict(item) for item in raw if isinstance(item, dict)]
        return sorted(records, key=lambda record: record.uploaded_at, reverse=True)

    def upsert(self, item: UploadItem, status: str) -> HistoryRecord:
        finished_at = item.finished_at or datetime.now().astimezone()
        record = HistoryRecord(
            id=item.id,
            name=item.name,
            file_type=item.extension.upper(),
            size=item.size,
            uploaded_at=finished_at.isoformat(timespec="seconds"),
            status=status,
            conflict_result=item.conflict_result,
            source="Mô phỏng cục bộ" if item.used_mock_fallback else "API server",
        )
        records = [existing for existing in self.list_records() if existing.id != item.id]
        records.insert(0, record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps([asdict(value) for value in records], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
        return record
