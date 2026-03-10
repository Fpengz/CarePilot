"""Module for test api auth cookie resolution."""

from collections.abc import Generator

import pytest
from apps.api.dietary_api.main import create_app
from fastapi.testclient import TestClient

from dietary_guardian.config.settings import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _force_in_memory_auth_backend(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "in_memory")
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login_and_get_cookie(client: TestClient, *, email: str, password: str) -> tuple[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    cookie = response.cookies.get("dg_session")
    assert cookie is not None
    session_id = response.json()["session"]["session_id"]
    assert isinstance(session_id, str)
    return cookie, session_id


def test_require_session_accepts_live_session_when_duplicate_cookie_contains_expired_first() -> None:
    app = create_app()
    client = TestClient(app)
    signer = app.state.ctx.session_signer

    # Create an old signed token and immediately expire it by destroying its session record.
    old_cookie, old_session_id = _login_and_get_cookie(client, email="member@example.com", password="member-pass")
    assert old_cookie
    app.state.ctx.auth_store.destroy_session(old_session_id)

    live_cookie, _ = _login_and_get_cookie(client, email="member@example.com", password="member-pass")
    assert live_cookie

    probe_client = TestClient(app)
    headers = {"cookie": f"dg_session={old_cookie}; dg_session={live_cookie}"}
    me = probe_client.get("/api/v1/auth/me", headers=headers)

    ttl = int(app.state.ctx.settings.auth.session_ttl_seconds)
    assert signer.unsign(old_cookie, max_age_seconds=ttl) is not None
    assert signer.unsign(live_cookie, max_age_seconds=ttl) is not None
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "member@example.com"


def test_require_session_accepts_live_session_when_duplicate_cookie_contains_invalid_first() -> None:
    app = create_app()
    client = TestClient(app)
    live_cookie, _ = _login_and_get_cookie(client, email="admin@example.com", password="admin-pass")
    assert live_cookie

    probe_client = TestClient(app)
    headers = {"cookie": f"dg_session=invalid.not-a-signed-token; dg_session={live_cookie}"}
    me = probe_client.get("/api/v1/auth/me", headers=headers)
    household = probe_client.get("/api/v1/households/current", headers=headers)

    assert me.status_code == 200
    assert household.status_code == 200


def test_require_session_returns_session_expired_when_all_signed_candidates_are_dead() -> None:
    app = create_app()
    client = TestClient(app)
    cookie_a, session_id_a = _login_and_get_cookie(client, email="member@example.com", password="member-pass")
    cookie_b, session_id_b = _login_and_get_cookie(client, email="member@example.com", password="member-pass")
    app.state.ctx.auth_store.destroy_session(session_id_a)
    app.state.ctx.auth_store.destroy_session(session_id_b)

    probe_client = TestClient(app)
    headers = {"cookie": f"dg_session={cookie_a}; dg_session={cookie_b}"}
    response = probe_client.get("/api/v1/auth/me", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "session expired"


def test_require_session_returns_invalid_session_when_all_candidates_are_bad_signatures() -> None:
    app = create_app()
    probe_client = TestClient(app)
    headers = {"cookie": "dg_session=bad-token-1; dg_session=bad-token-2"}

    response = probe_client.get("/api/v1/auth/me", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid session"
