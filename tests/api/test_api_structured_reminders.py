"""API tests for structured reminder definitions and occurrences."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from apps.api.carepilot_api.main import create_app
from fastapi.testclient import TestClient

from care_pilot.config.app import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_structured_reminder_env(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(
    client: TestClient,
    email: str = "member@example.com",
    password: str = "member-pass",
) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200


def test_structured_reminder_generate_list_and_action_flow(
    sqlite_structured_reminder_env: None,
) -> None:
    client = TestClient(create_app())
    _login(client)

    created = client.post(
        "/api/v1/medications/regimens",
        json={
            "medication_name": "Metformin",
            "dosage_text": "500mg",
            "timing_type": "fixed_time",
            "fixed_time": "20:00",
            "offset_minutes": 0,
            "slot_scope": [],
            "max_daily_doses": 1,
            "active": True,
        },
    )
    assert created.status_code == 200

    generated = client.post("/api/v1/reminders/generate")
    assert generated.status_code == 200

    definitions = client.get("/api/v1/reminders/definitions")
    assert definitions.status_code == 200
    definitions_body = definitions.json()
    assert definitions_body["items"]
    assert definitions_body["items"][0]["schedule"]["pattern"] in {
        "daily_fixed_times",
        "meal_relative",
    }

    upcoming = client.get("/api/v1/reminders/upcoming")
    assert upcoming.status_code == 200
    upcoming_body = upcoming.json()
    assert upcoming_body["items"]
    occurrence_id = upcoming_body["items"][0]["id"]

    taken = client.post(
        f"/api/v1/reminders/occurrences/{occurrence_id}/actions",
        json={"action": "taken"},
    )
    assert taken.status_code == 200
    taken_body = taken.json()
    assert taken_body["occurrence"]["status"] == "completed"
    assert taken_body["occurrence"]["action"] == "taken"

    history = client.get("/api/v1/reminders/history")
    assert history.status_code == 200
    history_body = history.json()
    assert any(item["id"] == occurrence_id for item in history_body["items"])
