"""
Shared utilities for SQLite-backed reminder repositories.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from care_pilot.config.app import get_settings
from care_pilot.platform.persistence.sqlite_db import get_connection


def parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        settings = get_settings()
        parsed = parsed.replace(tzinfo=ZoneInfo(settings.app.timezone)).astimezone(UTC)
    return parsed


class SQLiteReminderRepositoryBase:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def _get_connection(self) -> Any:
        return get_connection(self.db_path)
