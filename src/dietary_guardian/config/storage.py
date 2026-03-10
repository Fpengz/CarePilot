"""Persistence and backend settings for app, auth, and household stores."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, populate_by_name=True)

    app_data_backend: Literal["sqlite"] = "sqlite"
    api_sqlite_db_path: str = "dietary_guardian_api.db"
    household_store_backend: Literal["sqlite"] = "sqlite"
    ephemeral_state_backend: Literal["in_memory", "redis"] = "in_memory"
    redis_url: str | None = None
    redis_namespace: str = "dietary_guardian"
    redis_default_ttl_seconds: int = Field(default=300, ge=1, le=86400)
    redis_lock_ttl_seconds: int = Field(default=30, ge=1, le=3600)
    redis_worker_signal_channel: str = "workers.ready"
