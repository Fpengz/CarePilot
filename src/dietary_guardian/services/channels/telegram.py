import json
from datetime import datetime, timezone
from urllib import error, request
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dietary_guardian.config.settings import get_settings
from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.medication import ReminderEvent
from dietary_guardian.services.channels.base import ChannelResult

logger = get_logger(__name__)


class TelegramChannel:
    name = "telegram"

    def __init__(self) -> None:
        settings = get_settings()
        self.bot_token = settings.telegram_bot_token or ""
        self.chat_id = settings.telegram_chat_id or ""
        self.dev_mode = settings.telegram_dev_mode
        self.app_timezone = settings.app_timezone
        self.request_timeout_seconds = settings.telegram_request_timeout_seconds

    def _build_endpoint(self) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def _format_scheduled_at(self, value: datetime) -> str:
        try:
            local_tz = ZoneInfo(self.app_timezone)
        except ZoneInfoNotFoundError:
            local_tz = timezone.utc
        dt = value if value.tzinfo is not None else value.replace(tzinfo=local_tz)
        local_dt = dt.astimezone(local_tz)
        return local_dt.isoformat(timespec="seconds")

    def _build_payload(self, reminder_event: ReminderEvent) -> dict[str, str]:
        text = (
            f"Medication reminder: {reminder_event.medication_name} "
            f"{reminder_event.dosage_text} at {self._format_scheduled_at(reminder_event.scheduled_at)}"
        )
        return {"chat_id": self.chat_id, "text": text}

    def send(self, reminder_event: ReminderEvent) -> ChannelResult:
        if not self.bot_token or not self.chat_id:
            logger.warning("telegram_send_missing_config event_id=%s", reminder_event.id)
            return ChannelResult(
                channel=self.name,
                success=False,
                error="missing telegram config",
                destination="telegram://unconfigured",
            )

        endpoint = self._build_endpoint()
        payload = self._build_payload(reminder_event)
        logger.info(
            "telegram_send_start event_id=%s destination=%s dev_mode=%s",
            reminder_event.id,
            endpoint,
            self.dev_mode,
        )

        if self.dev_mode:
            logger.info("telegram_send_dev_mode_skip_network event_id=%s", reminder_event.id)
            return ChannelResult(
                channel=self.name,
                success=True,
                delivered_at=datetime.now(timezone.utc),
                destination=endpoint,
            )

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
                    return ChannelResult(
                        channel=self.name,
                        success=False,
                        error=f"telegram http {resp.status}",
                        destination=endpoint,
                    )
                return ChannelResult(
                    channel=self.name,
                    success=True,
                    delivered_at=datetime.now(timezone.utc),
                    destination=endpoint,
                )
        except error.URLError as exc:
            logger.error("telegram_send_error event_id=%s error=%s", reminder_event.id, exc)
            return ChannelResult(
                channel=self.name,
                success=False,
                error=str(exc),
                destination=endpoint,
            )
