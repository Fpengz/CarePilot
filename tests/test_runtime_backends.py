from collections.abc import Generator

import pytest

from apps.api.dietary_api.deps import build_app_context, close_app_context
from dietary_guardian.config.settings import get_settings
from dietary_guardian.infrastructure.persistence import SQLiteAppStore, build_app_store


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def runtime_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("LLM_PROVIDER", "test")
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    monkeypatch.setenv("HOUSEHOLD_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("EPHEMERAL_STATE_BACKEND", "in_memory")
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def test_build_app_context_supports_redis_ephemeral_backend(
    runtime_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EPHEMERAL_STATE_BACKEND", "redis")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    _reset_settings_cache()

    ctx = build_app_context()
    try:
        assert ctx.settings.storage.ephemeral_state_backend == "redis"
        assert ctx.coordination_store is not None
        assert ctx.cache_store is not None
    finally:
        close_app_context(ctx)


def test_build_app_context_defaults_to_in_memory_ephemeral_backends(runtime_env: None) -> None:
    ctx = build_app_context()
    try:
        assert ctx.settings.storage.ephemeral_state_backend == "in_memory"
        assert ctx.coordination_store is not None
        assert ctx.cache_store is not None
    finally:
        close_app_context(ctx)


def test_exported_build_app_store_returns_sqlite_store_in_sqlite_mode(runtime_env: None) -> None:
    store = build_app_store(get_settings())
    try:
        assert isinstance(store, SQLiteAppStore)
    finally:
        store.close()


def test_build_app_context_uses_sqlite_backends_for_durable_state(runtime_env: None) -> None:
    ctx = build_app_context()
    try:
        assert ctx.settings.storage.app_data_backend == "sqlite"
        assert ctx.settings.auth.store_backend == "sqlite"
        assert ctx.settings.storage.household_store_backend == "sqlite"
    finally:
        close_app_context(ctx)
