"""Interface consumed by the UI controller.

Concrete adapters may use mock data, TCP, JSON, or MySQL, but widgets never
import any of those implementations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from PySide6.QtCore import SignalInstance

from udm10.client.models.history import HistoryEntry
from udm10.client.models.upload import ConflictPolicy, UploadItem


class UiDataProvider(Protocol):
    uploads_changed: SignalInstance
    history_changed: SignalInstance
    history_loading_changed: SignalInstance
    history_error: SignalInstance
    connection_changed: SignalInstance
    duplicate_detected: SignalInstance

    def current_uploads(self) -> tuple[UploadItem, ...]: ...

    def current_history(self) -> tuple[HistoryEntry, ...]: ...

    def add_files(self, paths: list[Path]) -> None: ...

    def retry_upload(self, upload_id: str) -> None: ...

    def remove_upload(self, upload_id: str) -> None: ...

    def resolve_duplicate(
        self, upload_id: str, policy: ConflictPolicy, apply_to_remaining: bool
    ) -> None: ...

    def refresh_history(self) -> None: ...

    def retry_connection(self) -> None: ...
