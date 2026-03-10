"""Module for test api medications."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from apps.api.dietary_api.main import create_app
from fastapi.testclient import TestClient

from dietary_guardian.config.settings import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_medications_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(client: TestClient, email: str = "member@example.com", password: str = "member-pass") -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def test_medication_regimen_crud_and_adherence_metrics(sqlite_medications_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    created = client.post(
        "/api/v1/medications/regimens",
        json={
            "medication_name": "Lisinopril",
            "dosage_text": "10mg",
            "timing_type": "fixed_time",
            "fixed_time": "09:00",
            "offset_minutes": 0,
            "slot_scope": [],
            "max_daily_doses": 1,
            "active": True,
        },
    )
    assert created.status_code == 200
    regimen_id = created.json()["regimen"]["id"]

    listed = client.get("/api/v1/medications/regimens")
    assert listed.status_code == 200
    assert any(item["id"] == regimen_id for item in listed.json()["items"])

    updated = client.patch(
        f"/api/v1/medications/regimens/{regimen_id}",
        json={"active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["regimen"]["active"] is False

    adherence = client.post(
        "/api/v1/medications/adherence-events",
        json={
            "regimen_id": regimen_id,
            "status": "taken",
            "scheduled_at": "2026-03-01T09:00:00+00:00",
            "taken_at": "2026-03-01T09:05:00+00:00",
            "source": "manual",
        },
    )
    assert adherence.status_code == 200

    metrics = client.get("/api/v1/medications/adherence-metrics?from=2026-03-01&to=2026-03-02")
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["totals"]["events"] == 1
    assert body["totals"]["taken"] == 1
    assert body["totals"]["adherence_rate"] == 1.0


def test_reminder_generation_uses_persisted_regimens(sqlite_medications_env: None) -> None:
    client = TestClient(create_app())
    _login(client)

    created = client.post(
        "/api/v1/medications/regimens",
        json={
            "medication_name": "Atorvastatin",
            "dosage_text": "20mg",
            "timing_type": "fixed_time",
            "fixed_time": "22:00",
            "offset_minutes": 0,
            "slot_scope": [],
            "max_daily_doses": 1,
            "active": True,
        },
    )
    assert created.status_code == 200

    generated = client.post("/api/v1/reminders/generate")
    assert generated.status_code == 200
    reminders = generated.json()["reminders"]
    assert any(item["medication_name"] == "Atorvastatin" for item in reminders)
