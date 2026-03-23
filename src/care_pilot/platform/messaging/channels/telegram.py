"""
Send reminder notifications via Telegram.

This module implements the Telegram channel adapter for reminder delivery.
"""

import json
from datetime import UTC, datetime
from urllib import error, request
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from care_pilot.config.app import get_settings
from care_pilot.features.safety.domain.alerts import OutboundMessage
from care_pilot.platform.messaging.channels.base import ChannelResult
from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)


class TelegramChannel:
    name = "telegram"

    def __init__(self) -> None:
        settings = get_settings()
        self.bot_token = settings.channels.telegram_bot_token or ""
        self.chat_id = settings.channels.telegram_chat_id or ""
        self.dev_mode = settings.channels.telegram_dev_mode
        self.app_timezone = settings.app.timezone
        self.request_timeout_seconds = settings.channels.telegram_request_timeout_seconds

    def _build_endpoint(self) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def _format_scheduled_at(self, value: datetime) -> str:
        try:
            local_tz = ZoneInfo(self.app_timezone)
        except ZoneInfoNotFoundError:
            local_tz = UTC
        dt = value if value.tzinfo is not None else value.replace(tzinfo=local_tz)
        local_dt = dt.astimezone(local_tz)
        return local_dt.isoformat(timespec="seconds")

    def _resolve_chat_id(self, destination: str | None) -> str:
        raw = (destination or "").strip()
        if not raw:
            return self.chat_id
        if raw.startswith("telegram://"):
            return raw[len("telegram://") :]
        return raw

    def _build_payload(self, message: OutboundMessage, chat_id: str) -> dict[str, str]:
        text = str(message.payload.get("body") or message.payload.get("message") or "Message")
        return {"chat_id": chat_id, "text": text}

    def _build_photo_payload(self, message: OutboundMessage, chat_id: str) -> dict[str, str]:
        attachments = message.attachments or []
        first = attachments[0] if attachments else {}
        photo_url = str(first.get("url") or "")
        caption = str(first.get("caption") or message.payload.get("body") or "Message")
        return {"chat_id": chat_id, "photo": photo_url, "caption": caption}

    def send(self, message: OutboundMessage, destination: str | None = None) -> ChannelResult:
        chat_id = self._resolve_chat_id(destination)
        if not self.bot_token or not chat_id:
            logger.warning("telegram_send_missing_config event_id=%s", message.alert_id)
            return ChannelResult(
                channel=self.name,
                success=False,
                error="missing telegram config",
                destination="telegram://unconfigured",
            )
        if not destination:
            logger.info(
                "telegram_send_default_destination event_id=%s chat_id=%s",
                message.alert_id,
                chat_id,
            )

        has_media = bool(message.attachments)
        endpoint = (
            f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
            if has_media
            else self._build_endpoint()
        )
        payload = (
            self._build_photo_payload(message, chat_id)
            if has_media
            else self._build_payload(message, chat_id)
        )
        if has_media and not payload.get("photo"):
            has_media = False
            endpoint = self._build_endpoint()
            payload = self._build_payload(message, chat_id)
        logger.info(
            "telegram_send_start event_id=%s destination=%s dev_mode=%s",
            message.alert_id,
            destination or endpoint,
            self.dev_mode,
        )

        if self.dev_mode:
            logger.info(
                "telegram_send_dev_mode_skip_network event_id=%s",
                message.alert_id,
            )
            result = ChannelResult(
                channel=self.name,
                success=True,
                delivered_at=datetime.now(UTC),
                destination=destination or endpoint,
            )
            logger.info(
                "telegram_send_complete event_id=%s success=%s error=%s",
                message.alert_id,
                result.success,
                result.error or "",
            )
            return result

        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.request_timeout_seconds) as resp:  # noqa: S310
                ok = 200 <= resp.status < 300
                if not ok:
                    result = ChannelResult(
                        channel=self.name,
                        success=False,
                        error=f"telegram http {resp.status}",
                        destination=destination or endpoint,
                    )
                    logger.warning(
                        "telegram_send_complete event_id=%s success=%s error=%s",
                        message.alert_id,
                        result.success,
                        result.error or "",
                    )
                    return result
            result = ChannelResult(
                channel=self.name,
                success=True,
                delivered_at=datetime.now(UTC),
                destination=destination or endpoint,
            )
            logger.info(
                "telegram_send_complete event_id=%s success=%s error=%s",
                message.alert_id,
                result.success,
                result.error or "",
            )
            return result
        except error.URLError as exc:
            logger.error(
                "telegram_send_error event_id=%s error=%s",
                message.alert_id,
                exc,
            )
            result = ChannelResult(
                channel=self.name,
                success=False,
                error=str(exc),
                destination=destination or endpoint,
            )
            logger.warning(
                "telegram_send_complete event_id=%s success=%s error=%s",
                message.alert_id,
                result.success,
                result.error or "",
            )
            return result
