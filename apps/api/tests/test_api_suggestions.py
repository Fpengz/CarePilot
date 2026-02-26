from collections.abc import Generator
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from apps.api.dietary_api.main import create_app
from dietary_guardian.config.settings import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_suggestions_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(client: TestClient, email: str = "member@example.com", password: str = "member-pass") -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def _meal_upload(client: TestClient) -> None:
    img = Image.new("RGB", (64, 64), color=(120, 210, 90))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    response = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", buf.getvalue(), "image/jpeg")},
        data={"runtime_mode": "local", "provider": "test"},
    )
    assert response.status_code == 200


def test_suggestions_generate_from_report_persists_and_lists(sqlite_suggestions_env: None) -> None:
    client = TestClient(create_app())
    _login(client)
    _meal_upload(client)

    create = client.post(
        "/api/v1/suggestions/generate-from-report",
        json={"text": "HbA1c 7.1 LDL 4.2 systolic bp 150 diastolic bp 95"},
    )

    assert create.status_code == 200
    body = create.json()
    assert "suggestion" in body
    suggestion = body["suggestion"]
    assert suggestion["suggestion_id"]
    assert suggestion["disclaimer"]
    assert suggestion["report_parse"]["readings"]
    assert suggestion["recommendation"]["localized_advice"]
    assert "workflow" in suggestion

    listing = client.get("/api/v1/suggestions")
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) == 1
    assert items[0]["suggestion_id"] == suggestion["suggestion_id"]
    assert items[0]["recommendation"]["safe"] in {True, False}

    detail = client.get(f"/api/v1/suggestions/{suggestion['suggestion_id']}")
    assert detail.status_code == 200
    assert detail.json()["suggestion"]["suggestion_id"] == suggestion["suggestion_id"]


def test_suggestions_generate_from_report_requires_meal_record(sqlite_suggestions_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    response = client.post(
        "/api/v1/suggestions/generate-from-report",
        json={"text": "HbA1c 7.1 LDL 4.2"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "no meal records available"


def test_suggestions_endpoints_require_auth(sqlite_suggestions_env: None) -> None:
    client = TestClient(create_app())

    create = client.post("/api/v1/suggestions/generate-from-report", json={"text": "HbA1c 7.1"})
    list_resp = client.get("/api/v1/suggestions")

    assert create.status_code == 401
    assert list_resp.status_code == 401
