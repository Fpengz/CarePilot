from collections.abc import Generator
from datetime import datetime, timedelta, timezone

import asyncio
import pytest
from fastapi.testclient import TestClient

from apps.api.dietary_api.main import create_app
from dietary_guardian.config.settings import get_settings
from dietary_guardian.services.alerting_service import OutboxWorker
from dietary_guardian.services.reminder_notification_service import dispatch_due_reminder_notifications


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _isolated_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("AUTH_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("API_SQLITE_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("AUTH_SQLITE_DB_PATH", str(tmp_path / "auth.db"))
    monkeypatch.setenv("USE_ALERT_OUTBOX_V2", "1")
    _reset_settings_cache()
    yield
    _reset_settings_cache()


def _login(client: TestClient, email: str = "member@example.com", password: str = "member-pass") -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def test_notification_preferences_round_trip_and_generation_materializes_schedule() -> None:
    app = create_app()
    client = TestClient(app)
    _login(client)

    update = client.put(
        "/api/v1/reminder-notification-preferences/default",
        json={
            "rules": [
                {"channel": "in_app", "offset_minutes": -30, "enabled": True},
                {"channel": "email", "offset_minutes": 0, "enabled": True},
            ]
        },
    )

    assert update.status_code == 200
    body = update.json()
    assert len(body["preferences"]) == 2

    listed = client.get("/api/v1/reminder-notification-preferences")
    assert listed.status_code == 200
    assert {item["channel"] for item in listed.json()["preferences"]} == {"in_app", "email"}

    generated = client.post("/api/v1/reminders/generate")
    assert generated.status_code == 200
    reminder_id = generated.json()["reminders"][0]["id"]

    schedules = client.get(f"/api/v1/reminders/{reminder_id}/notification-schedules")
    assert schedules.status_code == 200
    scheduled = schedules.json()["items"]
    assert len(scheduled) == 2
    assert {(item["channel"], item["offset_minutes"]) for item in scheduled} == {
        ("in_app", -30),
        ("email", 0),
    }


def test_dispatch_due_notifications_enqueues_and_delivers_due_schedule() -> None:
    app = create_app()
    client = TestClient(app)
    _login(client)

    pref = client.put(
        "/api/v1/reminder-notification-preferences/default",
        json={"rules": [{"channel": "in_app", "offset_minutes": 0, "enabled": True}]},
    )
    assert pref.status_code == 200

    generated = client.post("/api/v1/reminders/generate")
    assert generated.status_code == 200
    reminder_id = generated.json()["reminders"][0]["id"]

    repo = app.state.ctx.app_store
    schedules = repo.list_scheduled_notifications(reminder_id=reminder_id)
    assert schedules
    schedule_id = schedules[0].id
    repo.set_scheduled_notification_trigger_at(schedule_id, datetime.now(timezone.utc) - timedelta(minutes=1))

    queued = dispatch_due_reminder_notifications(repository=repo, now=datetime.now(timezone.utc))
    assert [item.scheduled_notification_id for item in queued] == [schedule_id]

    worker = OutboxWorker(repo, max_attempts=2, concurrency=2)
    results = asyncio.run(worker.process_once(alert_id=schedule_id))
    assert results
    refreshed = repo.get_scheduled_notification(schedule_id)
    assert refreshed is not None
    assert refreshed.status == "delivered"

    logs = repo.list_notification_logs(reminder_id=reminder_id)
    assert any(item.event_type == "delivered" for item in logs)


def test_confirming_reminder_cancels_future_pending_notifications() -> None:
    app = create_app()
    client = TestClient(app)
    _login(client)

    pref = client.put(
        "/api/v1/reminder-notification-preferences/default",
        json={"rules": [{"channel": "in_app", "offset_minutes": 0, "enabled": True}]},
    )
    assert pref.status_code == 200

    generated = client.post("/api/v1/reminders/generate")
    assert generated.status_code == 200
    reminder_id = generated.json()["reminders"][0]["id"]

    schedules_before = client.get(f"/api/v1/reminders/{reminder_id}/notification-schedules")
    assert schedules_before.status_code == 200
    assert schedules_before.json()["items"][0]["status"] == "pending"

    confirmed = client.post(f"/api/v1/reminders/{reminder_id}/confirm", json={"confirmed": True})
    assert confirmed.status_code == 200

    schedules_after = client.get(f"/api/v1/reminders/{reminder_id}/notification-schedules")
    assert schedules_after.status_code == 200
    assert all(item["status"] == "cancelled" for item in schedules_after.json()["items"])


def test_notification_endpoints_round_trip_and_logs_visible_after_delivery() -> None:
    app = create_app()
    client = TestClient(app)
    _login(client)

    endpoint_update = client.put(
        "/api/v1/reminder-notification-endpoints",
        json={
            "endpoints": [
                {"channel": "email", "destination": "member@example.com", "verified": True},
                {"channel": "sms", "destination": "+15551234567", "verified": False},
            ]
        },
    )
    assert endpoint_update.status_code == 200
    assert {item["channel"] for item in endpoint_update.json()["endpoints"]} == {"email", "sms"}

    endpoint_list = client.get("/api/v1/reminder-notification-endpoints")
    assert endpoint_list.status_code == 200
    assert len(endpoint_list.json()["endpoints"]) == 2

    pref = client.put(
        "/api/v1/reminder-notification-preferences/default",
        json={"rules": [{"channel": "email", "offset_minutes": 0, "enabled": True}]},
    )
    assert pref.status_code == 200

    generated = client.post("/api/v1/reminders/generate")
    assert generated.status_code == 200
    reminder_id = generated.json()["reminders"][0]["id"]

    repo = app.state.ctx.app_store
    schedule = repo.list_scheduled_notifications(reminder_id=reminder_id)[0]
    repo.set_scheduled_notification_trigger_at(schedule.id, datetime.now(timezone.utc) - timedelta(minutes=1))
    dispatch_due_reminder_notifications(repository=repo, now=datetime.now(timezone.utc))
    asyncio.run(OutboxWorker(repo, max_attempts=2, concurrency=2).process_once(alert_id=schedule.id))

    logs = client.get(f"/api/v1/reminders/{reminder_id}/notification-logs")
    assert logs.status_code == 200
    body = logs.json()
    assert body["items"]
    assert any(item["event_type"] == "delivered" for item in body["items"])
