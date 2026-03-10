from apps.api.dietary_api.main import create_app
from fastapi.testclient import TestClient


def _login(client: TestClient, email: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def test_alert_trigger_requires_admin_scope() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    response = client.post(
        "/api/v1/alerts/trigger",
        json={
            "alert_type": "manual_test_alert",
            "severity": "warning",
            "message": "hello",
            "destinations": ["in_app"],
        },
    )

    assert response.status_code == 403


def test_alert_trigger_returns_tool_result_outbox_timeline_and_workflow_trace() -> None:
    client = TestClient(create_app())
    _login(client, "admin@example.com", "admin-pass")

    response = client.post(
        "/api/v1/alerts/trigger",
        json={
            "alert_type": "manual_test_alert",
            "severity": "warning",
            "message": "hello",
            "destinations": ["in_app"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tool_result"]["success"] is True
    assert body["workflow"]["workflow_name"] == "alert_only"
    assert body["outbox_timeline"]


def test_workflow_trace_lookup_by_correlation_id() -> None:
    client = TestClient(create_app())
    _login(client, "admin@example.com", "admin-pass")

    trigger = client.post(
        "/api/v1/alerts/trigger",
        json={
            "alert_type": "manual_test_alert",
            "severity": "warning",
            "message": "hello",
            "destinations": ["in_app"],
        },
    )
    assert trigger.status_code == 200
    corr = trigger.json()["workflow"]["correlation_id"]

    response = client.get(f"/api/v1/workflows/{corr}")

    assert response.status_code == 200
    assert response.json()["workflow_name"] == "replay"
    assert response.json()["replayed"] is True


def test_alert_timeline_not_found_uses_domain_code() -> None:
    client = TestClient(create_app())
    _login(client, "admin@example.com", "admin-pass")

    response = client.get("/api/v1/alerts/alert_missing/timeline")

    assert response.status_code == 404
    body = response.json()
    assert body["detail"] == "alert not found"
    assert body["error"]["code"] == "alerts.not_found"
