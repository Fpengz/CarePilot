from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from apps.api.dietary_api.main import create_app


def _login(client: TestClient, email: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def _meal_upload(client: TestClient) -> None:
    img = Image.new("RGB", (64, 64), color=(0, 255, 0))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    response = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", buf.getvalue(), "image/jpeg")},
        data={"runtime_mode": "local", "provider": "test"},
    )
    assert response.status_code == 200


def test_reports_parse_text_returns_readings_and_snapshot() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    response = client.post(
        "/api/v1/reports/parse",
        json={"source": "pasted_text", "text": "HbA1c 7.1 LDL 4.2 systolic bp 150 diastolic bp 95"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["readings"]
    assert "hba1c" in body["snapshot"]["biomarkers"]
    assert "high_ldl" in body["snapshot"]["risk_flags"]


def test_recommendations_generate_uses_latest_meal_and_snapshot() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")
    _meal_upload(client)
    parse_resp = client.post(
        "/api/v1/reports/parse",
        json={"source": "pasted_text", "text": "HbA1c 7.1 LDL 4.2"},
    )
    assert parse_resp.status_code == 200

    response = client.post("/api/v1/recommendations/generate")

    assert response.status_code == 200
    body = response.json()
    assert "recommendation" in body
    assert "workflow" in body
    assert body["recommendation"]["safe"] in {True, False}
