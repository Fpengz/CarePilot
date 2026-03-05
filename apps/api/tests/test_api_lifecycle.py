from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from apps.api.dietary_api.deps import build_app_context
from apps.api.dietary_api.deps import close_app_context
from apps.api.dietary_api.main import create_app
from dietary_guardian.config.settings import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_lifecycle_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def test_app_lifecycle_closes_resources_on_shutdown(sqlite_lifecycle_env: None) -> None:
    app = create_app()
    ctx = app.state.ctx
    closed = {"repository": False, "auth_store": False, "household_store": False}

    def close_repository() -> None:
        closed["repository"] = True

    def close_auth_store() -> None:
        closed["auth_store"] = True

    def close_household_store() -> None:
        closed["household_store"] = True

    ctx.repository.close = close_repository
    ctx.auth_store.close = close_auth_store
    ctx.household_store.close = close_household_store

    with TestClient(app) as client:
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200

    assert closed == {"repository": True, "auth_store": True, "household_store": True}


def test_app_rebuilds_owned_context_on_lifespan_restart(sqlite_lifecycle_env: None) -> None:
    app = create_app()

    with TestClient(app) as client:
        first_login = client.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"})
        assert first_login.status_code == 200

    with TestClient(app) as client:
        second_login = client.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )
        assert second_login.status_code == 200


def test_app_does_not_close_caller_managed_context(sqlite_lifecycle_env: None) -> None:
    caller_ctx = build_app_context()
    app = create_app(caller_ctx)
    closed = {"repository": False, "auth_store": False, "household_store": False}

    def close_repository() -> None:
        closed["repository"] = True

    def close_auth_store() -> None:
        closed["auth_store"] = True

    def close_household_store() -> None:
        closed["household_store"] = True

    setattr(caller_ctx.repository, "close", close_repository)
    setattr(caller_ctx.auth_store, "close", close_auth_store)
    setattr(caller_ctx.household_store, "close", close_household_store)

    with TestClient(app) as client:
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200

    assert closed == {"repository": False, "auth_store": False, "household_store": False}
    close_app_context(caller_ctx)


def test_app_context_exposes_runtime_store_aliases(sqlite_lifecycle_env: None) -> None:
    ctx = build_app_context()
    try:
        assert ctx.app_store is ctx.repository
        assert ctx.cache_store is not None
        assert ctx.coordination_store is not None
    finally:
        close_app_context(ctx)
