from datetime import datetime
from urllib import request

from dietary_guardian.models.medication import ReminderEvent
from dietary_guardian.services.channels.telegram import TelegramChannel


def _event() -> ReminderEvent:
    return ReminderEvent(
        id="evt-1",
        user_id="u1",
        medication_name="Metformin",
        scheduled_at=datetime(2026, 2, 24, 12, 0),
        dosage_text="500mg",
    )


def test_telegram_dev_mode_skips_network(monkeypatch) -> None:
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


def test_telegram_missing_config_returns_failure(monkeypatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    channel = TelegramChannel()
    result = channel.send(_event())

    assert result.success is False
    assert "missing telegram config" in (result.error or "")
