from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from apps.api.dietary_api.main import create_app


def _jpeg_bytes() -> bytes:
    img = Image.new("RGB", (64, 64), color=(255, 0, 0))
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


def _jpeg_bytes_with_color(color: tuple[int, int, int]) -> bytes:
    img = Image.new("RGB", (64, 64), color=color)
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
    assert "summary" in body
    assert "output_envelope" in body
    assert "workflow" in body
    assert body["workflow"]["workflow_name"] == "meal_analysis"
    assert isinstance(body["summary"]["meal_name"], str)
    assert isinstance(body["summary"]["confidence"], float)
    assert body["summary"]["confidence"] >= 0.0
    assert isinstance(body["summary"]["estimated_calories"], (int, float))
    assert isinstance(body["summary"]["flags"], list)
    assert isinstance(body["summary"]["portion_size"], str)
    assert "needs_manual_review" in body["summary"]


def test_meal_analyze_rejects_empty_file_payload() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    response = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", b"", "image/jpeg")},
        data={"runtime_mode": "local", "provider": "test"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "empty upload"


def test_meal_analyze_rejects_missing_content_type() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    response = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", _jpeg_bytes(), "")},
        data={"runtime_mode": "local", "provider": "test"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "unsupported image format"


def test_meal_records_limit_query_truncates_response() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    for color in [(255, 0, 0), (0, 255, 0), (0, 0, 255)]:
        response = client.post(
            "/api/v1/meal/analyze",
            files={"file": ("meal.jpg", _jpeg_bytes_with_color(color), "image/jpeg")},
            data={"runtime_mode": "local", "provider": "test"},
        )
        assert response.status_code == 200

    all_records = client.get("/api/v1/meal/records")
    limited = client.get("/api/v1/meal/records?limit=2")

    assert all_records.status_code == 200
    assert limited.status_code == 200
    assert len(all_records.json()["records"]) >= 3
    assert len(limited.json()["records"]) == 2
