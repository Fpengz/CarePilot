from collections.abc import Generator

import pytest
from apps.api.dietary_api.main import create_app
from fastapi.testclient import TestClient

from dietary_guardian.config.settings import get_settings


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture
def sqlite_reminder_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.sqlite3"))
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.sqlite3"))
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(client: TestClient, email: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def test_generate_list_and_confirm_reminders_flow() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    generated = client.post("/api/v1/reminders/generate")
    assert generated.status_code == 200
    generated_body = generated.json()
    assert generated_body["reminders"]
    event_id = generated_body["reminders"][0]["id"]

    listed = client.get("/api/v1/reminders")
    assert listed.status_code == 200
    assert listed.json()["metrics"]["reminders_sent"] >= 1

    confirmed = client.post(f"/api/v1/reminders/{event_id}/confirm", json={"confirmed": True})
    assert confirmed.status_code == 200
    assert confirmed.json()["event"]["status"] == "acknowledged"

    listed_after = client.get("/api/v1/reminders")
    assert listed_after.status_code == 200
    assert listed_after.json()["metrics"]["meal_confirmed_yes"] >= 1


def test_confirm_reminder_missing_event_uses_domain_code() -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    response = client.post("/api/v1/reminders/rem_missing/confirm", json={"confirmed": True})

    assert response.status_code == 404
    body = response.json()
    assert body["detail"] == "reminder not found"
    assert body["error"]["code"] == "reminders.not_found"


def test_mobility_settings_round_trip(sqlite_reminder_env: None) -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    default_response = client.get("/api/v1/reminders/mobility-settings")
    assert default_response.status_code == 200
    assert default_response.json()["settings"] == {
        "enabled": False,
        "interval_minutes": 120,
        "active_start_time": "08:00",
        "active_end_time": "20:00",
    }

    updated = client.put(
        "/api/v1/reminders/mobility-settings",
        json={
            "enabled": True,
            "interval_minutes": 120,
            "active_start_time": "09:00",
            "active_end_time": "13:00",
        },
    )

    assert updated.status_code == 200
    assert updated.json()["settings"] == {
        "enabled": True,
        "interval_minutes": 120,
        "active_start_time": "09:00",
        "active_end_time": "13:00",
    }

    fetched = client.get("/api/v1/reminders/mobility-settings")
    assert fetched.status_code == 200
    assert fetched.json() == updated.json()


def test_generate_reminders_includes_mobility_events_when_enabled(sqlite_reminder_env: None) -> None:
    client = TestClient(create_app())
    _login(client, "member@example.com", "member-pass")

    update = client.put(
        "/api/v1/reminders/mobility-settings",
        json={
            "enabled": True,
            "interval_minutes": 120,
            "active_start_time": "09:00",
            "active_end_time": "13:00",
        },
    )
    assert update.status_code == 200

    generated = client.post("/api/v1/reminders/generate")

    assert generated.status_code == 200
    reminders = generated.json()["reminders"]
    medication = [item for item in reminders if item["reminder_type"] == "medication"]
    mobility = [item for item in reminders if item["reminder_type"] == "mobility"]
    assert medication
    assert len(mobility) == 3
    assert {item["title"] for item in mobility} == {"Time to move"}
    assert all("stretch" in item["body"].lower() for item in mobility)


def test_generate_reminders_publishes_worker_signal(sqlite_reminder_env: None) -> None:
    app = create_app()
    client = TestClient(app)
    _login(client, "member@example.com", "member-pass")

    generated = client.post("/api/v1/reminders/generate")

    assert generated.status_code == 200
    signals = app.state.ctx.coordination_store.drain_signals("reminders.ready")
    assert signals
    assert signals[0]["user_id"] == "user_001"
