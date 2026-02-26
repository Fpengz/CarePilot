from fastapi.testclient import TestClient

from apps.api.dietary_api.main import create_app
from dietary_guardian.config.settings import Settings


def test_login_sets_session_cookie_and_returns_user() -> None:
    client = TestClient(create_app())

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


def test_me_requires_auth() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_me_returns_authenticated_user_after_login() -> None:
    client = TestClient(create_app())
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
    client = TestClient(create_app())

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
    assert client.post("/api/v1/auth/login", json={"email": "patient@example.com", "password": "patient-pass"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "caregiver@example.com", "password": "caregiver-pass"}).status_code == 401


def test_logout_clears_session() -> None:
    client = TestClient(create_app())
    client.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"})

    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 401


def test_logout_is_idempotent_without_session() -> None:
    client = TestClient(create_app())

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    set_cookie = response.headers.get("set-cookie", "")
    assert "dg_session=" in set_cookie
    assert "Max-Age=0" in set_cookie or "max-age=0" in set_cookie


def test_me_rejects_corrupted_session_payload_with_401() -> None:
    app = create_app()
    client = TestClient(app)

    login = client.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"})
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
    member_client_a = TestClient(app)
    member_client_b = TestClient(app)
    admin_client = TestClient(app)

    login_a = member_client_a.post(
        "/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"}
    )
    login_b = member_client_b.post(
        "/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"}
    )
    admin_login = admin_client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin-pass"}
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
    assert admin_login.json()["session"]["session_id"] not in {item["session_id"] for item in sessions}


def test_revoke_specific_session_revokes_current_and_clears_cookie() -> None:
    client = TestClient(create_app())
    login = client.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"})
    assert login.status_code == 200
    session_id = login.json()["session"]["session_id"]

    revoke = client.post(f"/api/v1/auth/sessions/{session_id}/revoke")

    assert revoke.status_code == 200
    assert revoke.json() == {"ok": True, "revoked": True}
    assert "dg_session=" in revoke.headers.get("set-cookie", "")
    assert client.get("/api/v1/auth/me").status_code == 401


def test_revoke_other_users_session_returns_404() -> None:
    app = create_app()
    member_client = TestClient(app)
    admin_client = TestClient(app)

    member_login = member_client.post(
        "/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"}
    )
    admin_login = admin_client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin-pass"}
    )
    assert member_login.status_code == 200
    assert admin_login.status_code == 200
    member_session_id = member_login.json()["session"]["session_id"]

    revoke = admin_client.post(f"/api/v1/auth/sessions/{member_session_id}/revoke")

    assert revoke.status_code == 404


def test_revoke_others_keeps_current_session_only() -> None:
    app = create_app()
    client_a = TestClient(app)
    client_b = TestClient(app)

    login_a = client_a.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"})
    login_b = client_b.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"})
    assert login_a.status_code == 200
    assert login_b.status_code == 200

    revoke_others = client_a.post("/api/v1/auth/sessions/revoke-others")

    assert revoke_others.status_code == 200
    assert revoke_others.json() == {"ok": True, "revoked_count": 1}
    assert client_a.get("/api/v1/auth/me").status_code == 200
    assert client_b.get("/api/v1/auth/me").status_code == 401


def test_patch_profile_updates_current_session_and_me() -> None:
    client = TestClient(create_app())
    login = client.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"})
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
    client = TestClient(app)
    relogin_client = TestClient(app)
    login = client.post("/api/v1/auth/login", json={"email": "helper@example.com", "password": "helper-pass"})
    assert login.status_code == 200

    patch = client.patch("/api/v1/auth/profile", json={"display_name": "Casey Family"})
    assert patch.status_code == 200
    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 200

    relogin = relogin_client.post(
        "/api/v1/auth/login", json={"email": "helper@example.com", "password": "helper-pass"}
    )
    assert relogin.status_code == 200
    assert relogin.json()["user"]["display_name"] == "Casey Family"


def test_patch_profile_rejects_empty_update() -> None:
    client = TestClient(create_app())
    login = client.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"})
    assert login.status_code == 200

    patch = client.patch("/api/v1/auth/profile", json={})

    assert patch.status_code == 400
    assert patch.json()["detail"] == "no profile changes requested"


def test_login_locks_after_repeated_failures_and_then_allows_after_success() -> None:
    client = TestClient(create_app())
    max_attempts = Settings(llm_provider="test").auth_login_max_failed_attempts

    for _ in range(max_attempts):
        failed = client.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "wrong-pass"})
        assert failed.status_code == 401

    locked = client.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"})
    assert locked.status_code == 429

    app = create_app()
    app.state.ctx.auth_store._login_failures["member@example.com"] = {
        "failed_count": max_attempts - 1,
        "window_started_at": "2000-01-01T00:00:00+00:00",
        "lockout_until": None,
    }
    reset_client = TestClient(app)
    success = reset_client.post(
        "/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"}
    )
    assert success.status_code == 200
    next_failed = reset_client.post(
        "/api/v1/auth/login", json={"email": "member@example.com", "password": "wrong-pass"}
    )
    assert next_failed.status_code == 401
    assert "too many login attempts" not in next_failed.text.lower()


def test_auth_audit_events_admin_only_and_bounded() -> None:
    app = create_app()
    member_client = TestClient(app)
    admin_client = TestClient(app)

    member_client.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "wrong-pass"})
    member_client.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"})
    admin_login = admin_client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "admin-pass"})
    assert admin_login.status_code == 200

    member_forbidden = member_client.get("/api/v1/auth/audit-events")
    assert member_forbidden.status_code == 403

    admin_events = admin_client.get("/api/v1/auth/audit-events", params={"limit": 2})
    assert admin_events.status_code == 200
    items = admin_events.json()["items"]
    assert len(items) == 2
    assert all(item["event_type"] in {"login_success", "login_failed", "login_locked"} for item in items)
    assert any(item["event_type"] == "login_success" for item in items)


def test_patch_password_updates_credentials_and_revokes_other_sessions() -> None:
    app = create_app()
    client_a = TestClient(app)
    client_b = TestClient(app)
    relogin_client = TestClient(app)

    login_a = client_a.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"})
    login_b = client_b.post("/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"})
    assert login_a.status_code == 200
    assert login_b.status_code == 200

    patch = client_a.patch(
        "/api/v1/auth/password",
        json={"current_password": "member-pass", "new_password": "member-pass-2"},
    )

    assert patch.status_code == 200
    assert patch.json() == {"ok": True, "revoked_other_sessions": 1}
    assert client_a.get("/api/v1/auth/me").status_code == 200
    assert client_b.get("/api/v1/auth/me").status_code == 401

    old_login = relogin_client.post(
        "/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"}
    )
    new_login = relogin_client.post(
        "/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass-2"}
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_patch_password_rejects_wrong_current_password() -> None:
    client = TestClient(create_app())
    login = client.post("/api/v1/auth/login", json={"email": "helper@example.com", "password": "helper-pass"})
    assert login.status_code == 200

    patch = client.patch(
        "/api/v1/auth/password",
        json={"current_password": "wrong-pass", "new_password": "helper-pass-2"},
    )

    assert patch.status_code == 400
    assert patch.json()["detail"] == "current password is incorrect"


def test_patch_password_rejects_weak_or_reused_password() -> None:
    client = TestClient(create_app())
    login = client.post("/api/v1/auth/login", json={"email": "helper@example.com", "password": "helper-pass"})
    assert login.status_code == 200

    weak = client.patch(
        "/api/v1/auth/password",
        json={"current_password": "helper-pass", "new_password": "short"},
    )
    reused = client.patch(
        "/api/v1/auth/password",
        json={"current_password": "helper-pass", "new_password": "helper-pass"},
    )

    assert weak.status_code == 400
    assert weak.json()["detail"] == "new password must be at least 8 characters"
    assert reused.status_code == 400
    assert reused.json()["detail"] == "new password must differ from current password"
