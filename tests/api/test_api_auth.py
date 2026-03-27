"""Module for test api auth."""

import time
from collections.abc import Generator
from types import SimpleNamespace
from typing import cast

import pytest
from apps.api.carepilot_api.deps import AppContext
from apps.api.carepilot_api.main import create_app
from fastapi.testclient import TestClient

from care_pilot.config.app import AppSettings as Settings, get_settings
from care_pilot.platform.auth import InMemoryAuthStore, SessionSigner


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


def _build_settings(**overrides: object) -> Settings:
    return Settings.model_validate(overrides)


def _create_auth_only_app():
    settings = _build_settings(
        llm={"provider": "test"},
        auth={"store_backend": "in_memory"},
    )
    ctx = SimpleNamespace(
        settings=settings,
        auth_store=InMemoryAuthStore(settings),
        session_signer=SessionSigner(settings.auth.session_secret),
    )
    return create_app(ctx=cast(AppContext, ctx))


@pytest.fixture(autouse=True)
def _force_in_memory_auth_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "in_memory")
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def test_login_sets_session_cookie_and_returns_user() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "admin-pass"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["user"]["email"] == "admin@example.com"
        assert body["user"]["account_role"] == "admin"
        assert body["user"]["profile_mode"] == "self"
        assert "alert:trigger" in body["user"]["scopes"]
        assert "dg_session" in response.cookies


def test_signup_creates_member_session_and_returns_principal() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "newuser@example.com",
                "password": "newuser-pass",
                "display_name": "New User",
                "profile_mode": "self",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["user"]["email"] == "newuser@example.com"
        assert body["user"]["account_role"] == "member"
        assert body["user"]["profile_mode"] == "self"
        assert "meal:read" in body["user"]["scopes"]
        assert "dg_session" in response.cookies
        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["user"]["email"] == "newuser@example.com"


def test_signup_rejects_duplicate_email() -> None:
    with TestClient(create_app()) as client:
        first = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "dupe@example.com",
                "password": "dupe-pass-01",
                "display_name": "First",
            },
        )
        second = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "dupe@example.com",
                "password": "dupe-pass-02",
                "display_name": "Second",
            },
        )

        assert first.status_code == 200
        assert second.status_code == 409
        assert second.json()["detail"] == "email already registered"


@pytest.mark.filterwarnings("ignore::ResourceWarning")
def test_signup_rejects_short_password() -> None:
    with TestClient(create_app()) as client:
        response = client.post(

            "/api/v1/auth/signup",
            json={
                "email": "shortpw@example.com",
                "password": "short",
                "display_name": "Short Pw",
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "password must be at least 12 characters"


def test_me_requires_auth() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401


def test_me_returns_authenticated_user_after_login() -> None:
    with TestClient(create_app()) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "helper@example.com", "password": "helper-pass"},
        )
        assert login.status_code == 200

        me = client.get("/api/v1/auth/me")

        assert me.status_code == 200
        assert me.json()["user"]["account_role"] == "member"
        assert me.json()["user"]["profile_mode"] == "caregiver"
        assert "alert:trigger" not in me.json()["user"]["scopes"]


def test_removed_roles_cannot_login() -> None:
    with TestClient(create_app()) as client:
        old_clinician = client.post(
            "/api/v1/auth/login",
            json={"email": "clinician@example.com", "password": "clinician-pass"},
        )
        old_operator = client.post(
            "/api/v1/auth/login",
            json={"email": "operator@example.com", "password": "operator-pass"},
        )

        assert old_clinician.status_code == 401
        assert old_operator.status_code == 401
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": "patient@example.com", "password": "patient-pass"},
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/auth/login",
                json={
                    "email": "caregiver@example.com",
                    "password": "caregiver-pass",
                },
            ).status_code
            == 401
        )


def test_logout_clears_session() -> None:
    with TestClient(create_app()) as client:
        client.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )

        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200

        me = client.get("/api/v1/auth/me")
        assert me.status_code == 401


def test_logout_is_idempotent_without_session() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 200
        assert response.json() == {"ok": True}
        set_cookie = response.headers.get("set-cookie", "")
        assert "dg_session=" in set_cookie
        assert "Max-Age=0" in set_cookie or "max-age=0" in set_cookie


def test_login_cookie_uses_configured_samesite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COOKIE_SAMESITE", "strict")
    _reset_settings_cache()
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )

        assert response.status_code == 200
        set_cookie = response.headers.get("set-cookie", "").lower()
        assert "samesite=strict" in set_cookie


def test_me_rejects_corrupted_session_payload_with_401() -> None:
    app = create_app()
    with TestClient(app) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )
        assert login.status_code == 200
        session_id = login.json()["session"]["session_id"]

        issued_at = app.state.ctx.auth_store._sessions[session_id]["issued_at"]
        app.state.ctx.auth_store._sessions[session_id] = {
            "session_id": session_id,
            "user_id": "user_001",
            "issued_at": issued_at,
        }

        me = client.get("/api/v1/auth/me")
        assert me.status_code == 401
        assert me.json()["detail"] == "invalid session"


def test_list_sessions_returns_current_and_same_user_sessions_only() -> None:
    app = create_app()
    with TestClient(app) as member_client_a, TestClient(app) as member_client_b, TestClient(app) as admin_client:
        login_a = member_client_a.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )
        login_b = member_client_b.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )
        admin_login = admin_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "admin-pass"},
        )
        assert login_a.status_code == 200
        assert login_b.status_code == 200
        assert admin_login.status_code == 200

        response = member_client_a.get("/api/v1/auth/sessions")

        assert response.status_code == 200
        sessions = response.json()["sessions"]
        assert len(sessions) == 2
        assert sum(1 for item in sessions if item["is_current"]) == 1
        assert login_a.json()["session"]["session_id"] in {item["session_id"] for item in sessions}
        assert login_b.json()["session"]["session_id"] in {item["session_id"] for item in sessions}
        assert admin_login.json()["session"]["session_id"] not in {
            item["session_id"] for item in sessions
        }


def test_revoke_specific_session_revokes_current_and_clears_cookie() -> None:
    with TestClient(create_app()) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )
        assert login.status_code == 200
        session_id = login.json()["session"]["session_id"]

        revoke = client.post(f"/api/v1/auth/sessions/{session_id}/revoke")

        assert revoke.status_code == 200
        assert revoke.json() == {"ok": True, "revoked": True}
        assert "dg_session=" in revoke.headers.get("set-cookie", "")
        assert client.get("/api/v1/auth/me").status_code == 401


def test_revoke_other_users_session_returns_404() -> None:
    app = create_app()
    with TestClient(app) as member_client, TestClient(app) as admin_client:
        member_login = member_client.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )
        admin_login = admin_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "admin-pass"},
        )
        assert member_login.status_code == 200
        assert admin_login.status_code == 200
        member_session_id = member_login.json()["session"]["session_id"]

        revoke = admin_client.post(f"/api/v1/auth/sessions/{member_session_id}/revoke")

        assert revoke.status_code == 404


def test_revoke_others_keeps_current_session_only() -> None:
    app = create_app()
    with TestClient(app) as client_a, TestClient(app) as client_b:
        login_a = client_a.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )
        login_b = client_b.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )
        assert login_a.status_code == 200
        assert login_b.status_code == 200

        revoke_others = client_a.post("/api/v1/auth/sessions/revoke-others")

        assert revoke_others.status_code == 200
        assert revoke_others.json() == {"ok": True, "revoked_count": 1}
        assert client_a.get("/api/v1/auth/me").status_code == 200
        assert client_b.get("/api/v1/auth/me").status_code == 401


def test_patch_profile_updates_current_session_and_me() -> None:
    with TestClient(create_app()) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )
        assert login.status_code == 200

        patch = client.patch(
            "/api/v1/auth/profile",
            json={"display_name": "Alex Wellness", "profile_mode": "caregiver"},
        )

        assert patch.status_code == 200
        body = patch.json()
        assert body["user"]["display_name"] == "Alex Wellness"
        assert body["user"]["profile_mode"] == "caregiver"
        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["user"]["display_name"] == "Alex Wellness"
        assert me.json()["user"]["profile_mode"] == "caregiver"


def test_patch_profile_persists_for_future_sessions() -> None:
    app = create_app()
    with TestClient(app) as client, TestClient(app) as relogin_client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "helper@example.com", "password": "helper-pass"},
        )
        assert login.status_code == 200

        patch = client.patch("/api/v1/auth/profile", json={"display_name": "Casey Family"})
        assert patch.status_code == 200
        logout = client.post("/api/v1/auth/logout")
        assert logout.status_code == 200

        relogin = relogin_client.post(
            "/api/v1/auth/login",
            json={"email": "helper@example.com", "password": "helper-pass"},
        )
        assert relogin.status_code == 200
        assert relogin.json()["user"]["display_name"] == "Casey Family"


def test_patch_profile_rejects_empty_update() -> None:
    with TestClient(create_app()) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )
        assert login.status_code == 200

        patch = client.patch("/api/v1/auth/profile", json={})

        assert patch.status_code == 400
        assert patch.json()["detail"] == "no profile changes requested"


def test_login_locks_after_repeated_failures_and_then_allows_after_lockout_expiry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    max_attempts = 2
    lockout_seconds = 1
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILED_ATTEMPTS", str(max_attempts))
    monkeypatch.setenv("AUTH_LOGIN_LOCKOUT_SECONDS", str(lockout_seconds))
    monkeypatch.setenv("AUTH_LOGIN_FAILURE_WINDOW_SECONDS", "1")
    _reset_settings_cache()
    with TestClient(create_app()) as client:
        for _ in range(max_attempts):
            failed = client.post(
                "/api/v1/auth/login",
                json={"email": "member@example.com", "password": "wrong-pass"},
            )
            assert failed.status_code == 401

        locked = client.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )
        assert locked.status_code == 429

        time.sleep(lockout_seconds + 0.1)
        success = client.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )
        assert success.status_code == 200
        next_failed = client.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "wrong-pass"},
        )
        assert next_failed.status_code == 401
        assert "too many login attempts" not in next_failed.text.lower()


def test_login_normalizes_email_for_authentication_and_lockout() -> None:
    app = create_app()
    with TestClient(app) as client:
        failed = client.post(
            "/api/v1/auth/login",
            json={"email": " MEMBER@EXAMPLE.COM ", "password": "wrong-pass"},
        )
        assert failed.status_code == 401

        success = client.post(
            "/api/v1/auth/login",
            json={"email": " MEMBER@EXAMPLE.COM ", "password": "member-pass"},
        )
        assert success.status_code == 200


def test_auth_audit_events_admin_only_and_bounded() -> None:
    app = create_app()
    with TestClient(app) as member_client, TestClient(app) as admin_client:
        member_client.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "wrong-pass"},
        )
        member_client.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )
        admin_login = admin_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "admin-pass"},
        )
        assert admin_login.status_code == 200

        member_forbidden = member_client.get("/api/v1/auth/audit-events")
        assert member_forbidden.status_code == 403

        admin_events = admin_client.get("/api/v1/auth/audit-events", params={"limit": 2})
        assert admin_events.status_code == 200
        items = admin_events.json()["items"]
        assert len(items) == 2
        assert all(
            item["event_type"] in {"login_success", "login_failed", "login_locked"} for item in items
        )
        assert any(item["event_type"] == "login_success" for item in items)


def test_patch_password_updates_credentials_and_revokes_other_sessions() -> None:
    app = create_app()
    with TestClient(app) as client_a, TestClient(app) as client_b, TestClient(app) as relogin_client:
        login_a = client_a.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )
        login_b = client_b.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )
        assert login_a.status_code == 200
        assert login_b.status_code == 200

        patch = client_a.patch(
            "/api/v1/auth/password",
            json={
                "current_password": "member-pass",
                "new_password": "member-pass-2",
            },
        )

        assert patch.status_code == 200
        assert patch.json() == {"ok": True, "revoked_other_sessions": 1}
        assert client_a.get("/api/v1/auth/me").status_code == 200
        assert client_b.get("/api/v1/auth/me").status_code == 401

        old_login = relogin_client.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass"},
        )
        new_login = relogin_client.post(
            "/api/v1/auth/login",
            json={"email": "member@example.com", "password": "member-pass-2"},
        )
        assert old_login.status_code == 401
        assert new_login.status_code == 200


def test_patch_password_rejects_wrong_current_password() -> None:
    with TestClient(create_app()) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "helper@example.com", "password": "helper-pass"},
        )
        assert login.status_code == 200

        patch = client.patch(
            "/api/v1/auth/password",
            json={
                "current_password": "wrong-pass",
                "new_password": "helper-pass-2",
            },
        )

        assert patch.status_code == 400
        assert patch.json()["detail"] == "current password is incorrect"


def test_patch_password_rejects_weak_or_reused_password() -> None:
    with TestClient(create_app()) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "helper@example.com", "password": "helper-pass"},
        )
        assert login.status_code == 200

        weak = client.patch(
            "/api/v1/auth/password",
            json={"current_password": "helper-pass", "new_password": "short"},
        )
        reused = client.patch(
            "/api/v1/auth/password",
            json={
                "current_password": "helper-pass",
                "new_password": "helper-pass",
            },
        )

        assert weak.status_code == 400
        assert weak.json()["detail"] == "new password must be at least 12 characters"
        assert reused.status_code == 400
        assert reused.json()["detail"] == "new password must differ from current password"


def test_settings_default_auth_backend_is_sqlite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AUTH_STORE_BACKEND", raising=False)
    settings = _build_settings(llm={"provider": "test"})
    assert settings.auth.store_backend == "sqlite"


def test_auth_api_supports_sqlite_backend_with_persistence_across_app_instances(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "auth.sqlite3"
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(db_path))
    _reset_settings_cache()

    app_a = create_app()
    with TestClient(app_a) as client_a:
        signup = client_a.post(
            "/api/v1/auth/signup",
            json={
                "email": "sqlite-user@example.com",
                "password": "sqlite-pass-1",
                "display_name": "SQLite User",
                "profile_mode": "self",
            },
        )
        assert signup.status_code == 200

        me = client_a.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["user"]["email"] == "sqlite-user@example.com"

    # New app instance, same sqlite file -> account persists.
    _reset_settings_cache()
    app_b = create_app()
    with TestClient(app_b) as client_b:
        login = client_b.post(
            "/api/v1/auth/login",
            json={"email": "sqlite-user@example.com", "password": "sqlite-pass-1"},
        )
        assert login.status_code == 200
        assert login.json()["user"]["email"] == "sqlite-user@example.com"

