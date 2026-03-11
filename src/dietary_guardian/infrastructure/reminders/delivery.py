from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Optional

from dietary_guardian.domain.reminders.models import ReminderDispatchResult, ReminderEvent

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class TelegramDeliveryConfig:
    bot_token: str = ""
    chat_id: str = ""
    dev_mode: bool = True


class MockDeliveryAdapter:
    """
    Safe default adapter for local development and testing.
    """

    def send(self, event: ReminderEvent) -> ReminderDispatchResult:
        logger.info(
            "[MOCK DELIVERY] channel=%s user_id=%s reminder_id=%s payload=%s",
            event.channel,
            event.user_id,
            event.reminder_id,
            event.payload,
        )
        return ReminderDispatchResult(
            success=True,
            provider_msg_id=f"mock-{uuid.uuid4().hex[:12]}",
            error=None,
        )


class TelegramDeliveryAdapter:
    """
    Telegram delivery adapter.

    Current implementation is intentionally conservative:
    - in dev_mode: simulate success
    - in non-dev mode without API client: return explicit failure

    This keeps the boundary stable while allowing quick integration with
    the rest of the reminder system.
    """

    def __init__(self, config: TelegramDeliveryConfig) -> None:
        self.config = config

    def _extract_text(self, event: ReminderEvent) -> str:
        try:
            payload = json.loads(event.payload)
            if isinstance(payload, dict):
                return str(payload.get("message") or payload.get("payload", {}).get("message") or "")
        except Exception:
            pass
        return ""

    def send(self, event: ReminderEvent) -> ReminderDispatchResult:
        message_text = self._extract_text(event)

        if self.config.dev_mode:
            logger.info(
                "[TELEGRAM DEV MODE] chat_id=%s reminder_id=%s text=%s",
                self.config.chat_id,
                event.reminder_id,
                message_text or event.payload,
            )
            return ReminderDispatchResult(
                success=True,
                provider_msg_id=f"tg-dev-{uuid.uuid4().hex[:12]}",
                error=None,
            )

        if not self.config.bot_token or not self.config.chat_id:
            return ReminderDispatchResult(
                success=False,
                provider_msg_id=None,
                error="telegram bot_token/chat_id missing",
            )

        # Placeholder for real Telegram API integration.
        # Can be replaced with requests/httpx implementation later.
        logger.warning(
            "TelegramDeliveryAdapter is running in non-dev mode, "
            "but no live API transport is implemented yet."
        )
        return ReminderDispatchResult(
            success=False,
            provider_msg_id=None,
            error="telegram live transport not implemented",
        )


class WebhookDeliveryAdapter:
    """
    Generic placeholder adapter for external channels such as WhatsApp.
    """

    def __init__(self, *, endpoint_name: str = "external-webhook", dev_mode: bool = True) -> None:
        self.endpoint_name = endpoint_name
        self.dev_mode = dev_mode

    def send(self, event: ReminderEvent) -> ReminderDispatchResult:
        if self.dev_mode:
            logger.info(
                "[WEBHOOK DEV MODE] endpoint=%s reminder_id=%s payload=%s",
                self.endpoint_name,
                event.reminder_id,
                event.payload,
            )
            return ReminderDispatchResult(
                success=True,
                provider_msg_id=f"webhook-dev-{uuid.uuid4().hex[:12]}",
                error=None,
            )

        return ReminderDispatchResult(
            success=False,
            provider_msg_id=None,
            error=f"{self.endpoint_name} live transport not implemented",
        )


def build_delivery_adapter(
    *,
    channel: str = "telegram",
    telegram_bot_token: str = "",
    telegram_chat_id: str = "",
    telegram_dev_mode: bool = True,
    fallback_to_mock: bool = True,
) -> Any:
    """
    Simple factory used by workers/bootstrap code.
    """
    channel_norm = channel.lower().strip()

    if channel_norm == "telegram":
        return TelegramDeliveryAdapter(
            TelegramDeliveryConfig(
                bot_token=telegram_bot_token,
                chat_id=telegram_chat_id,
                dev_mode=telegram_dev_mode,
            )
        )

    if channel_norm in {"whatsapp", "sms", "email", "webhook"}:
        return WebhookDeliveryAdapter(endpoint_name=channel_norm, dev_mode=True)

    if fallback_to_mock:
        return MockDeliveryAdapter()

    raise ValueError(f"Unsupported delivery channel: {channel}")