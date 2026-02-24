from datetime import datetime

from dietary_guardian.models.medication import ReminderEvent
from dietary_guardian.services.notification_service import dispatch_reminder, send_in_app, send_push


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
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("TELEGRAM_DEV_MODE", "1")
    results = dispatch_reminder(_event(), ["telegram"])
    assert len(results) == 1
    assert results[0].channel == "telegram"
    assert results[0].success is True
    assert "api.telegram.org" in (results[0].destination or "")
