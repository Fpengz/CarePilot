"""API tests for patient medical card."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from apps.api.carepilot_api.main import create_app
from fastapi.testclient import TestClient

from care_pilot.config.app import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_patient_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    monkeypatch.setenv("LLM_PROVIDER", "test")
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"email": "member@example.com", "password": "member-pass"}
    )
    assert response.status_code == 200


def test_patient_medical_card_endpoint_returns_markdown(
    sqlite_patient_env: None,
) -> None:
    client = TestClient(create_app())
    _login(client)

    response = client.get("/api/v1/companion/patient-card")

    assert response.status_code == 200
    body = response.json()
    assert "markdown" in body
    assert "informational purposes only" in body["markdown"]
