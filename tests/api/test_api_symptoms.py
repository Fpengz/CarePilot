"""Module for test api symptoms."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from apps.api.dietary_api.main import create_app
from fastapi.testclient import TestClient

from dietary_guardian.config.app import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_symptoms_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(client: TestClient, email: str = "member@example.com", password: str = "member-pass") -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def test_symptom_checkin_create_list_summary(sqlite_symptoms_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    created = client.post(
        "/api/v1/symptoms/check-ins",
        json={
            "severity": 3,
            "symptom_codes": ["headache", "fatigue"],
            "free_text": "Mild headache today",
            "context": {"after_meal": True},
        },
    )
    assert created.status_code == 200

    listed = client.get("/api/v1/symptoms/check-ins")
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1

    summary = client.get("/api/v1/symptoms/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["total_count"] == 1
    assert body["average_severity"] == 3.0
    assert body["top_symptoms"][0]["code"] == "headache"


def test_symptom_checkin_red_flag_is_counted(sqlite_symptoms_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    response = client.post(
        "/api/v1/symptoms/check-ins",
        json={
            "severity": 5,
            "symptom_codes": ["chest_pain"],
            "free_text": "Chest pain and trouble breathing",
        },
    )
    assert response.status_code == 200
    assert response.json()["item"]["safety"]["decision"] == "escalate"

    summary = client.get("/api/v1/symptoms/summary")
    assert summary.status_code == 200
    assert summary.json()["red_flag_count"] == 1
