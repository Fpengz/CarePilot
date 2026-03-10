"""Module for test api clinical cards."""

from __future__ import annotations

import io
from collections.abc import Generator

import pytest
from apps.api.dietary_api.main import create_app
from fastapi.testclient import TestClient
from PIL import Image

from dietary_guardian.config.settings import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_clinical_cards_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    monkeypatch.setenv("MEAL_ANALYZE_PROVIDER", "test")
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(client: TestClient, email: str = "member@example.com", password: str = "member-pass") -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def _meal_upload(client: TestClient) -> None:
    img = Image.new("RGB", (8, 8), color=(255, 200, 120))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    response = client.post(
        "/api/v1/meal/analyze",
        files={"file": ("meal.jpg", buf.getvalue(), "image/jpeg")},
        data={"provider": "test"},
    )
    assert response.status_code == 200


def test_clinical_card_generate_list_get(sqlite_clinical_cards_env: None) -> None:
    client = TestClient(create_app())
    _login(client)
    _meal_upload(client)
    parsed = client.post("/api/v1/reports/parse", json={"source": "pasted_text", "text": "LDL: 4.2 HbA1c: 7.1"})
    assert parsed.status_code == 200

    created = client.post("/api/v1/clinical-cards/generate", json={"format": "sectioned"})
    assert created.status_code == 200
    body = created.json()
    card_id = body["card"]["id"]
    assert set(body["card"]["sections"].keys()) == {"subjective", "objective", "assessment", "plan"}
    assert "deltas" in body["card"]

    listed = client.get("/api/v1/clinical-cards")
    assert listed.status_code == 200
    assert any(item["id"] == card_id for item in listed.json()["items"])

    fetched = client.get(f"/api/v1/clinical-cards/{card_id}")
    assert fetched.status_code == 200
    assert fetched.json()["card"]["id"] == card_id
