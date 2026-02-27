from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from apps.api.dietary_api.main import create_app


def _login(client: TestClient, email: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def _meal_upload(client: TestClient) -> None:
    img = Image.new("RGB", (48, 48), color=(255, 0, 0))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    response = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", buf.getvalue(), "image/jpeg")},
        data={"runtime_mode": "local", "provider": "test"},
    )
    assert response.status_code == 200


def test_meal_records_endpoint_returns_saved_records() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")
    _meal_upload(client)

    response = client.get("/api/v1/meal/records")

    assert response.status_code == 200
    body = response.json()
    assert body["records"]
    assert "meal_state" in body["records"][0]


def test_alert_timeline_endpoint_returns_outbox_rows() -> None:
    client = TestClient(create_app())
    _login(client, "admin@example.com", "admin-pass")
    trigger = client.post(
        "/api/v1/alerts/trigger",
        json={
            "alert_type": "manual_test_alert",
            "severity": "warning",
            "message": "Manual end-to-end alert verification",
            "destinations": ["in_app"],
        },
    )
    assert trigger.status_code == 200
    alert_id = str(trigger.json()["outbox_timeline"][0]["alert_id"])

    response = client.get(f"/api/v1/alerts/{alert_id}/timeline")

    assert response.status_code == 200
    body = response.json()
    assert body["alert_id"] == alert_id
    assert body["outbox_timeline"]


def test_workflows_list_endpoint_returns_items_for_admin() -> None:
    client = TestClient(create_app())
    _login(client, "admin@example.com", "admin-pass")
    trigger = client.post(
        "/api/v1/alerts/trigger",
        json={
            "alert_type": "manual_test_alert",
            "severity": "warning",
            "message": "Manual end-to-end alert verification",
            "destinations": ["in_app"],
        },
    )
    assert trigger.status_code == 200
    client.post("/api/v1/auth/logout")
    _login(client, "admin@example.com", "admin-pass")

    response = client.get("/api/v1/workflows")

    assert response.status_code == 200
    body = response.json()
    assert body["items"]
    assert {"workflow_name", "correlation_id"} <= set(body["items"][0].keys())
    assert isinstance(body["items"][0]["event_count"], int)
    assert "latest_event_at" in body["items"][0]
