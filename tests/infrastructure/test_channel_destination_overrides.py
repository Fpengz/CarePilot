"""
Validate that notification sinks honor per-user destinations.

These tests ensure per-account reminder endpoints override global defaults so
delivery routes reflect user settings.
"""

from dietary_guardian.config.app import get_settings
from dietary_guardian.features.safety.domain.alerts import AlertMessage
from dietary_guardian.platform.messaging.channels.sinks import TelegramSink


def test_telegram_sink_prefers_payload_destination(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "fallback")
    monkeypatch.setenv("TELEGRAM_DEV_MODE", "1")
    message = AlertMessage(
        alert_id="alert-1",
        type="reminder_notification",
        severity="info",
        payload={
            "user_id": "user-1",
            "medication_name": "Metformin",
            "dosage_text": "500mg",
            "scheduled_at": "2026-03-12T12:00:00",
            "destination": "telegram://user-chat",
        },
        destinations=["telegram"],
        correlation_id="corr-1",
    )

    result = TelegramSink().send(message)

    assert result.success is True
    assert result.destination == "telegram://user-chat"
    get_settings.cache_clear()
