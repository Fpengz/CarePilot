"""
Build persistence-layer repositories and stores.

This module provides factory helpers for constructing persistence adapters.
"""

from __future__ import annotations

from care_pilot.config.app import AppSettings as Settings

from .contracts import AppStoreBackend
from .sqlite_repository import SQLiteRepository


class SQLiteAppStore(SQLiteRepository):
    """Concrete SQLite implementation of the application store."""

    pass


def build_app_store(settings: Settings) -> AppStoreBackend:
    return SQLiteAppStore(settings.storage.api_sqlite_db_path)
