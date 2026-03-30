"""Module for test api lifecycle."""

from collections.abc import Generator

import pytest
from apps.api.carepilot_api.main import create_app

from care_pilot.config.app import get_settings
from care_pilot.platform.app_context import build_app_context, close_app_context


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


@pytest.mark.anyio
async def test_close_app_context_is_awaited_by_lifespan() -> None:
    from unittest.mock import AsyncMock

    import apps.api.carepilot_api.main as main_mod

    app = create_app()
    ctx = app.state.ctx
    app.state.ctx_owned = True

    # Mock close_app_context directly in the module
    mock_close = AsyncMock()
    import pytest
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(main_mod, "close_app_context", mock_close)

        # Manually trigger lifespan
        async with main_mod.app_lifespan(app):
            pass

    assert mock_close.called
    # It should be called with the context
    assert mock_close.call_args[0][0] is ctx



@pytest.mark.anyio
async def test_app_rebuilds_owned_context_on_lifespan_restart(
    sqlite_lifecycle_env: None,
) -> None:
    from httpx import ASGITransport, AsyncClient
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )
        assert first_login.status_code == 200

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        second_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )
        assert second_login.status_code == 200


@pytest.mark.anyio
async def test_app_does_not_close_caller_managed_context(
    sqlite_lifecycle_env: None,
) -> None:
    caller_ctx = build_app_context()
    app = create_app(caller_ctx)
    closed = {
        "repository": False,
        "auth_store": False,
        "household_store": False,
    }

    async def close_repository(*args: object, **kwargs: object) -> None:
        closed["repository"] = True

    async def close_auth_store(*args: object, **kwargs: object) -> None:
        closed["auth_store"] = True

    async def close_household_store(*args: object, **kwargs: object) -> None:
        closed["household_store"] = True

    caller_ctx.app_store.close = close_repository  # type: ignore[invalid-assignment]
    caller_ctx.auth_store.close = close_auth_store  # type: ignore[invalid-assignment]
    caller_ctx.household_store.close = close_household_store  # type: ignore[invalid-assignment]

    from httpx import ASGITransport, AsyncClient
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/live")
        assert response.status_code == 200

    assert closed == {
        "repository": False,
        "auth_store": False,
        "household_store": False,
    }
    await close_app_context(caller_ctx)


@pytest.mark.anyio
async def test_app_context_exposes_runtime_store_aliases(
    sqlite_lifecycle_env: None,
) -> None:
    ctx = build_app_context()
    try:
        assert ctx.app_store is not None
        assert ctx.stores is not None
        assert ctx.cache_store is not None
        assert ctx.coordination_store is not None
    finally:
        await close_app_context(ctx)


@pytest.mark.anyio
async def test_cors_uses_configured_methods_and_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("API_CORS_METHODS", "GET,POST")
    monkeypatch.setenv("API_CORS_HEADERS", "Content-Type")
    _reset_settings_cache()
    app = create_app()
    from httpx import ASGITransport, AsyncClient
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
    _reset_settings_cache()

    assert response.status_code == 200
    allow_methods = response.headers.get("access-control-allow-methods", "").upper()
    allow_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "POST" in allow_methods
    assert "DELETE" not in allow_methods
    assert "content-type" in allow_headers
