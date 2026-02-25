from fastapi.testclient import TestClient

from apps.api.dietary_api.main import create_app


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
