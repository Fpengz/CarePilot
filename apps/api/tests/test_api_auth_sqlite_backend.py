from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from apps.api.dietary_api.main import create_app
from dietary_guardian.config.settings import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_auth_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def test_sqlite_auth_profile_and_session_management_persist_across_app_instances(
    sqlite_auth_env: None,
) -> None:
    app = create_app()
    client_a = TestClient(app)
    client_b = TestClient(app)

    login_a = client_a.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"})
    login_b = client_b.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"})
    assert login_a.status_code == 200
    assert login_b.status_code == 200

    sessions = client_a.get("/api/v1/auth/sessions")
    assert sessions.status_code == 200
    assert len(sessions.json()["sessions"]) == 2

    patch = client_a.patch(
        "/api/v1/auth/profile",
        json={"display_name": "SQLite Member", "profile_mode": "caregiver"},
    )
    assert patch.status_code == 200
    assert patch.json()["user"]["display_name"] == "SQLite Member"
    assert patch.json()["user"]["profile_mode"] == "caregiver"

    revoke_others = client_a.post("/api/v1/auth/sessions/revoke-others")
    assert revoke_others.status_code == 200
    assert revoke_others.json()["revoked_count"] == 1
    assert client_b.get("/api/v1/auth/me").status_code == 401

    # New app instance on same sqlite DB sees updated profile.
    _reset_settings_cache()
    relogin_client = TestClient(create_app())
    relogin = relogin_client.post(
        "/api/v1/auth/login",
        json={"email": "member@example.com", "password": "member-pass"},
    )
    assert relogin.status_code == 200
    assert relogin.json()["user"]["display_name"] == "SQLite Member"
    assert relogin.json()["user"]["profile_mode"] == "caregiver"


def test_sqlite_auth_password_change_persists_and_emits_audit_events(sqlite_auth_env: None) -> None:
    app = create_app()
    client_a = TestClient(app)
    client_b = TestClient(app)
    admin_client = TestClient(app)

    assert client_a.post(
        "/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"}
    ).status_code == 200
    assert client_b.post(
        "/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"}
    ).status_code == 200
    assert admin_client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin-pass"}
    ).status_code == 200

    patch = client_a.patch(
        "/api/v1/auth/password",
        json={"current_password": "member-pass", "new_password": "member-pass-sqlite"},
    )
    assert patch.status_code == 200
    assert patch.json()["revoked_other_sessions"] == 1
    assert client_b.get("/api/v1/auth/me").status_code == 401

    relogin_client = TestClient(create_app())
    assert relogin_client.post(
        "/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"}
    ).status_code == 401
    assert relogin_client.post(
        "/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass-sqlite"}
    ).status_code == 200

    audit = admin_client.get("/api/v1/auth/audit-events", params={"limit": 20})
    assert audit.status_code == 200
    event_types = [item["event_type"] for item in audit.json()["items"]]
    assert "password_changed" in event_types


def test_sqlite_auth_audit_events_enforce_admin_scope(sqlite_auth_env: None) -> None:
    member_client = TestClient(create_app())
    login = member_client.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"})
    assert login.status_code == 200

    response = member_client.get("/api/v1/auth/audit-events")

    assert response.status_code == 403
