"""
Build persistence-layer repositories and stores.

This module provides factory helpers for constructing persistence adapters.
"""

from __future__ import annotations

from dietary_guardian.config.app import AppSettings as Settings

from .contracts import AppStoreBackend
from .sqlite_app_store import SQLiteAppStore


def build_app_store(settings: Settings) -> AppStoreBackend:
    return SQLiteAppStore(settings.storage.api_sqlite_db_path)
