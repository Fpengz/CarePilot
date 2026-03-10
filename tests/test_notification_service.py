"""Tests for notification service."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from dietary_guardian.config.settings import get_settings
from dietary_guardian.domain.alerts.models import AlertDeliveryResult, AlertMessage
from dietary_guardian.domain.notifications.models import ReminderEvent
from dietary_guardian.infrastructure.persistence import SQLiteRepository
from dietary_guardian.application.notifications.alert_dispatch import (
    dispatch_reminder,
    dispatch_reminder_async,
    send_in_app,
    send_push,
    trigger_alert,
)


def _event() -> ReminderEvent:
    return ReminderEvent(
        id="e1",
        user_id="u1",
        medication_name="Amlodipine",
        scheduled_at=datetime(2026, 2, 24, 11, 30),
        dosage_text="5mg",
    )


def test_send_in_app_success() -> None:
    result = send_in_app(_event())
    assert result.success is True
    assert result.channel == "in_app"


def test_dispatch_push_failure_does_not_block_in_app() -> None:
    results = dispatch_reminder(_event(), ["in_app", "push"], retries=1, force_push_fail=True)
    assert len(results) == 2
    assert results[0].success is True
    assert results[1].channel == "push"
    assert results[1].success is False
    assert results[1].attempts == 2


def test_send_push_success() -> None:
    result = send_push(_event())
    assert result.success is True
    assert result.channel == "push"


def test_dispatch_telegram_channel(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("TELEGRAM_DEV_MODE", "1")
    results = dispatch_reminder(_event(), ["telegram"])
    assert len(results) == 1
    assert results[0].channel == "telegram"
    assert results[0].success is True
    assert "api.telegram.org" in (results[0].destination or "")
    get_settings.cache_clear()


def test_dispatch_reminder_async_preserves_reminder_fields_for_telegram(monkeypatch, tmp_path) -> None:
    captured = {}

    def fake_send(self, reminder_event):  # noqa: ANN001
        captured["scheduled_at"] = reminder_event.scheduled_at
        captured["dosage_text"] = reminder_event.dosage_text
        captured["medication_name"] = reminder_event.medication_name
        return type(
            "Result",
            (),
            {
                "channel": "telegram",
                "success": True,
                "attempts": 1,
                "error": None,
                "destination": "telegram://test",
            },
        )()

    monkeypatch.setattr(
        "dietary_guardian.infrastructure.notifications.channels.telegram.TelegramChannel.send",
        fake_send,
    )

    event = _event()
    repo = SQLiteRepository(str(tmp_path / "alerts.db"))
    dispatch_reminder_async(event, ["telegram"], repository=repo)

    assert captured["scheduled_at"] == event.scheduled_at
    assert captured["scheduled_at"].tzinfo is None
    assert captured["dosage_text"] == event.dosage_text
    assert captured["medication_name"] == event.medication_name


def test_trigger_alert_returns_only_current_alert_deliveries(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ALERT_WORKER_CONCURRENCY", "1")
    get_settings.cache_clear()

    repo = SQLiteRepository(str(tmp_path / "alerts.db"))
    old_alert = AlertMessage(
        alert_id=str(uuid4()),
        type="old",
        severity="warning",
        payload={"message": "older"},
        destinations=["in_app"],
        correlation_id=str(uuid4()),
    )
    repo.enqueue_alert(old_alert)
    repo.reschedule_alert(
        old_alert.alert_id,
        "in_app",
        datetime.now(timezone.utc) - timedelta(seconds=5),
        attempt_count=0,
        error="",
    )

    alert, deliveries = trigger_alert(
        alert_type="manual_test",
        severity="warning",
        payload={"message": "new"},
        destinations=["in_app"],
        repository=repo,
    )

    assert deliveries
    assert all(item.event_id == alert.alert_id for item in deliveries)
    get_settings.cache_clear()


def test_dispatch_reminder_v2_preserves_force_push_fail_and_retries(monkeypatch, tmp_path) -> None:
    event = _event()
    repo = SQLiteRepository(str(tmp_path / "alerts.db"))

    results = dispatch_reminder(
        event,
        ["push"],
        retries=0,
        force_push_fail=True,
        repository=repo,
    )

    assert len(results) == 1
    assert results[0].channel == "push"
    assert results[0].success is False
    assert results[0].attempts == 1
    records = repo.list_alert_records(event.id)
    assert len(records) == 1
    assert records[0].state == "dead_letter"
    assert records[0].attempt_count == 1


def test_dispatch_reminder_v2_retries_until_success(monkeypatch, tmp_path) -> None:
    event = _event()
    repo = SQLiteRepository(str(tmp_path / "alerts.db"))
    attempts = {"count": 0}

    def flaky_push_send(self, message):  # noqa: ANN001
        del self
        attempts["count"] += 1
        success = attempts["count"] >= 2
        return AlertDeliveryResult(
            alert_id=message.alert_id,
            sink="push",
            success=success,
            attempt=1,
            destination="push://default",
            provider_reference="push",
            error=None if success else "push delivery failed",
        )

    monkeypatch.setattr("dietary_guardian.infrastructure.notifications.alert_outbox.PushSink.send", flaky_push_send)

    results = dispatch_reminder_async(
        event,
        ["push"],
        repository=repo,
        retries=2,
    )

    assert len(results) == 1
    assert results[0].channel == "push"
    assert results[0].success is True
    assert results[0].attempts == 2
    records = repo.list_alert_records(event.id)
    assert len(records) == 1
    assert records[0].state == "delivered"
    assert records[0].attempt_count == 2


def test_trigger_alert_drains_all_destinations_across_batches(monkeypatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ALERT_WORKER_CONCURRENCY", "1")
    get_settings.cache_clear()

    def fake_channel_send(self, reminder_event):  # noqa: ANN001
        channel_name = self.__class__.__name__.replace("Channel", "").lower()
        return type(
            "Result",
            (),
            {
                "channel": channel_name,
                "success": True,
                "attempts": 1,
                "error": None,
                "destination": f"{channel_name}://test",
                "delivered_at": None,
            },
        )()

    monkeypatch.setattr(
        "dietary_guardian.infrastructure.notifications.channels.telegram.TelegramChannel.send",
        fake_channel_send,
    )
    monkeypatch.setattr(
        "dietary_guardian.infrastructure.notifications.channels.whatsapp.WhatsAppChannel.send",
        fake_channel_send,
    )
    monkeypatch.setattr(
        "dietary_guardian.infrastructure.notifications.channels.wechat.WeChatChannel.send",
        fake_channel_send,
    )

    repo = SQLiteRepository(str(tmp_path / "alerts.db"))
    alert, deliveries = trigger_alert(
        alert_type="manual_test",
        severity="warning",
        payload={"message": "batch drain"},
        destinations=["in_app", "push", "telegram", "whatsapp", "wechat"],
        repository=repo,
    )

    assert {item.channel for item in deliveries} == {"in_app", "push", "telegram", "whatsapp", "wechat"}
    records = repo.list_alert_records(alert.alert_id)
    assert len(records) == 5
    assert all(item.state == "delivered" for item in records)
    get_settings.cache_clear()


def test_dispatch_reminder_v2_handles_sink_exceptions_as_delivery_failures(monkeypatch, tmp_path) -> None:
    event = _event()
    repo = SQLiteRepository(str(tmp_path / "alerts.db"))

    def broken_push_send(self, message):  # noqa: ANN001
        del self, message
        raise RuntimeError("push provider timeout")

    monkeypatch.setattr("dietary_guardian.infrastructure.notifications.alert_outbox.PushSink.send", broken_push_send)

    results = dispatch_reminder_async(
        event,
        ["push"],
        repository=repo,
        retries=0,
    )

    assert len(results) == 1
    assert results[0].channel == "push"
    assert results[0].success is False
    assert "timeout" in (results[0].error or "")
    records = repo.list_alert_records(event.id)
    assert len(records) == 1
    assert records[0].state == "dead_letter"
