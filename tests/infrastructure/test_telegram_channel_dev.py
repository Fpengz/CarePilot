"""Tests for telegram channel dev."""

from datetime import UTC, datetime
from urllib import request

from care_pilot.config.app import get_settings
from care_pilot.features.safety.domain.alerts.models import OutboundMessage
from care_pilot.platform.messaging.channels.telegram import TelegramChannel


def _event() -> OutboundMessage:
    return OutboundMessage(
        alert_id="evt-1",
        type="medication_reminder",
        severity="info",
        payload={
            "medication_name": "Metformin",
            "dosage_text": "500mg",
            "scheduled_at": datetime(2026, 2, 24, 12, 0),
        },
        destinations=["telegram"],
        correlation_id="corr-1",
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
    event = _event()
    event.payload["scheduled_at"] = datetime(2026, 2, 25, 9, 48, 3, tzinfo=UTC)
    payload = channel._build_payload(event, channel._resolve_chat_id(None))

    assert "+08:00" in payload["text"]
    assert "+00:00" not in payload["text"]
    get_settings.cache_clear()


def test_telegram_payload_preserves_naive_local_wall_clock(
    monkeypatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("TELEGRAM_DEV_MODE", "1")
    monkeypatch.setenv("APP_TIMEZONE", "Asia/Singapore")

    channel = TelegramChannel()
    event = _event()
    event.payload["scheduled_at"] = datetime(2026, 2, 25, 9, 48, 3)
    payload = channel._build_payload(event, channel._resolve_chat_id(None))

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
