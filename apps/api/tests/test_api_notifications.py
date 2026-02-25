from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from apps.api.dietary_api.main import create_app


def _login(client: TestClient, email: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def _meal_upload(client: TestClient, *, color: tuple[int, int, int] = (255, 0, 0)) -> None:
    img = Image.new("RGB", (48, 48), color=color)
    buf = BytesIO()
    img.save(buf, format="JPEG")
    response = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", buf.getvalue(), "image/jpeg")},
        data={"runtime_mode": "local", "provider": "test"},
    )
    assert response.status_code == 200


def test_notifications_requires_auth() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/notifications")

    assert response.status_code == 401


def test_notifications_list_returns_user_workflow_notifications() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")
    _meal_upload(client)

    response = client.get("/api/v1/notifications")

    assert response.status_code == 200
    body = response.json()
    assert body["unread_count"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["read"] is False
    assert item["category"] == "meal_analysis"
    assert item["workflow_name"] == "meal_analysis"
    assert item["user_id"]
    assert item["severity"] in {"info", "warning"}
    assert item["action_path"] == "/meals"
    assert isinstance(item["metadata"], dict)
    assert "manual_review" in item["metadata"]
    assert "meal_record_id" in item["metadata"]


def test_mark_notification_read_updates_unread_count() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")
    _meal_upload(client)

    listed = client.get("/api/v1/notifications")
    notification_id = listed.json()["items"][0]["id"]

    mark = client.post(f"/api/v1/notifications/{notification_id}/read")

    assert mark.status_code == 200
    marked_body = mark.json()
    assert marked_body["notification"]["id"] == notification_id
    assert marked_body["notification"]["read"] is True
    assert marked_body["unread_count"] == 0

    listed_again = client.get("/api/v1/notifications")
    assert listed_again.status_code == 200
    assert listed_again.json()["unread_count"] == 0
    assert listed_again.json()["items"][0]["read"] is True


def test_mark_all_notifications_read_marks_everything_for_user() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")
    _meal_upload(client)
    _meal_upload(client, color=(0, 255, 0))

    before = client.get("/api/v1/notifications")
    assert before.status_code == 200
    assert before.json()["unread_count"] == 2

    mark_all = client.post("/api/v1/notifications/read-all")

    assert mark_all.status_code == 200
    body = mark_all.json()
    assert body["updated_count"] == 2
    assert body["unread_count"] == 0

    after = client.get("/api/v1/notifications")
    assert after.status_code == 200
    assert after.json()["unread_count"] == 0
    assert all(item["read"] for item in after.json()["items"])
