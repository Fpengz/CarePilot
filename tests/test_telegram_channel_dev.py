"""Tests for telegram channel dev."""

from datetime import datetime, timezone
from urllib import request

from dietary_guardian.config.settings import get_settings
from dietary_guardian.domain.notifications.models import ReminderEvent
from dietary_guardian.infrastructure.notifications.channels.telegram import TelegramChannel


def _event() -> ReminderEvent:
    return ReminderEvent(
        id="evt-1",
        user_id="u1",
        medication_name="Metformin",
        scheduled_at=datetime(2026, 2, 24, 12, 0),
        dosage_text="500mg",
    )


def test_telegram_dev_mode_skips_network(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("TELEGRAM_DEV_MODE", "1")

    def _never_called(*args, **kwargs):
        raise AssertionError("urlopen should not be called in TELEGRAM_DEV_MODE")

    monkeypatch.setattr(request, "urlopen", _never_called)

    channel = TelegramChannel()
    result = channel.send(_event())

    assert result.success is True
    assert result.channel == "telegram"
    assert result.destination is not None
    assert "api.telegram.org" in result.destination
    get_settings.cache_clear()


def test_telegram_missing_config_returns_failure(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "")

    channel = TelegramChannel()
    result = channel.send(_event())

    assert result.success is False
    assert "missing telegram config" in (result.error or "")
    get_settings.cache_clear()


def test_telegram_payload_formats_local_timezone(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("TELEGRAM_DEV_MODE", "1")
    monkeypatch.setenv("APP_TIMEZONE", "Asia/Singapore")

    channel = TelegramChannel()
    event = _event().model_copy(update={"scheduled_at": datetime(2026, 2, 25, 9, 48, 3, tzinfo=timezone.utc)})
    payload = channel._build_payload(event)

    assert "+08:00" in payload["text"]
    assert "+00:00" not in payload["text"]
    get_settings.cache_clear()


def test_telegram_payload_preserves_naive_local_wall_clock(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("TELEGRAM_DEV_MODE", "1")
    monkeypatch.setenv("APP_TIMEZONE", "Asia/Singapore")

    channel = TelegramChannel()
    event = _event().model_copy(update={"scheduled_at": datetime(2026, 2, 25, 9, 48, 3)})
    payload = channel._build_payload(event)

    assert "09:48:03+08:00" in payload["text"]
    get_settings.cache_clear()


def test_telegram_channel_reads_timeout_from_settings(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("TELEGRAM_REQUEST_TIMEOUT_SECONDS", "42")

    channel = TelegramChannel()

    assert channel.request_timeout_seconds == 42.0
    get_settings.cache_clear()
