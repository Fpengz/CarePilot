from __future__ import annotations

from dietary_guardian.config.settings import Settings

from .contracts import AppStoreBackend
from .postgres_app_store import PostgresAppStore
from .sqlite_app_store import SQLiteAppStore


def build_app_store(settings: Settings) -> AppStoreBackend:
    if settings.app_data_backend == "sqlite":
        return SQLiteAppStore(settings.api_sqlite_db_path)
    return PostgresAppStore(dsn=str(settings.postgres_dsn))
