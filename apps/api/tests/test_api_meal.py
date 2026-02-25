from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from apps.api.dietary_api.main import create_app


def _jpeg_bytes() -> bytes:
    img = Image.new("RGB", (64, 64), color=(255, 0, 0))
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


def _login(client: TestClient, email: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def test_meal_analyze_requires_auth() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 401


def test_meal_analyze_returns_record_envelope_and_workflow() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    response = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", _jpeg_bytes(), "image/jpeg")},
        data={"runtime_mode": "local", "provider": "test"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "vision_result" in body
    assert "meal_record" in body
    assert "output_envelope" in body
    assert "workflow" in body
    assert body["workflow"]["workflow_name"] == "meal_analysis"
