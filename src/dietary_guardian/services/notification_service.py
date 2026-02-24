from datetime import datetime, timezone

from pydantic import BaseModel

from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.medication import ReminderEvent
from dietary_guardian.services.channels import TelegramChannel, WeChatChannel, WhatsAppChannel
from dietary_guardian.services.channels.base import ChannelResult

logger = get_logger(__name__)

class DeliveryResult(BaseModel):
    event_id: str
    channel: str
    success: bool
    attempts: int = 1
    error: str | None = None
    delivered_at: datetime | None = None
    destination: str | None = None


def send_in_app(reminder_event: ReminderEvent) -> DeliveryResult:
    destination = "app://inbox"
    logger.info(
        "send_in_app event_id=%s channel=in_app destination=%s attempt=1 success=true user_id=%s medication=%s",
        reminder_event.id,
        destination,
        reminder_event.user_id,
        reminder_event.medication_name,
    )
    return DeliveryResult(
        event_id=reminder_event.id,
        channel="in_app",
        success=True,
        delivered_at=datetime.now(timezone.utc),
        destination=destination,
    )


def send_push(reminder_event: ReminderEvent, force_fail: bool = False) -> DeliveryResult:
    destination = "push://default"
    logger.info(
        "send_push_attempt event_id=%s channel=push destination=%s attempt=1 user_id=%s medication=%s force_fail=%s",
        reminder_event.id,
        destination,
        reminder_event.user_id,
        reminder_event.medication_name,
        force_fail,
    )
    if force_fail:
        logger.warning(
            "send_push_failed event_id=%s channel=push destination=%s attempt=1 success=false reason=forced_failure",
            reminder_event.id,
            destination,
        )
        return DeliveryResult(
            event_id=reminder_event.id,
            channel="push",
            success=False,
            attempts=1,
            error="push delivery failed",
            destination=destination,
        )
    return DeliveryResult(
        event_id=reminder_event.id,
        channel="push",
        success=True,
        delivered_at=datetime.now(timezone.utc),
        destination=destination,
    )


def _channel_from_name(channel: str):
    if channel == "telegram":
        return TelegramChannel()
    if channel == "whatsapp":
        return WhatsAppChannel()
    if channel == "wechat":
        return WeChatChannel()
    return None


def _delivery_from_channel_result(
    event_id: str,
    channel_result: ChannelResult,
) -> DeliveryResult:
    return DeliveryResult(
        event_id=event_id,
        channel=channel_result.channel,
        success=channel_result.success,
        attempts=channel_result.attempts,
        error=channel_result.error,
        delivered_at=channel_result.delivered_at,
        destination=channel_result.destination,
    )


def dispatch_reminder(
    reminder_event: ReminderEvent,
    channels: list[str],
    retries: int = 2,
    force_push_fail: bool = False,
) -> list[DeliveryResult]:
    logger.info(
        "dispatch_reminder_start event_id=%s channels=%s retries=%s",
        reminder_event.id,
        channels,
        retries,
    )
    results: list[DeliveryResult] = []
    for channel in channels:
        if channel == "in_app":
            results.append(send_in_app(reminder_event))
            continue
        if channel == "push":
            attempt = 0
            latest = DeliveryResult(
                event_id=reminder_event.id,
                channel="push",
                success=False,
                attempts=0,
                error="push delivery failed",
                destination="push://default",
            )
            while attempt <= retries:
                attempt += 1
                latest = send_push(reminder_event, force_fail=force_push_fail)
                latest.attempts = attempt
                if latest.success:
                    logger.info(
                        "dispatch_reminder_push_delivered event_id=%s channel=push destination=%s attempt=%s success=true",
                        reminder_event.id,
                        latest.destination,
                        attempt,
                    )
                    break
            if not latest.success:
                logger.warning(
                    "dispatch_reminder_push_exhausted event_id=%s channel=push destination=%s attempt=%s success=false",
                    reminder_event.id,
                    latest.destination,
                    latest.attempts,
                )
            results.append(latest)
            continue

        extra_channel = _channel_from_name(channel)
        if extra_channel is not None:
            channel_result = extra_channel.send(reminder_event)
            logger.info(
                "dispatch_reminder_channel_result event_id=%s channel=%s success=%s destination=%s",
                reminder_event.id,
                channel_result.channel,
                channel_result.success,
                channel_result.destination,
            )
            results.append(_delivery_from_channel_result(reminder_event.id, channel_result))
            continue

        if channel != "push":
            logger.error(
                "dispatch_reminder_unknown_channel event_id=%s channel=%s",
                reminder_event.id,
                channel,
            )
            results.append(
                DeliveryResult(
                    event_id=reminder_event.id,
                    channel=channel,
                    success=False,
                    error="unknown channel",
                )
            )
            continue
    logger.info("dispatch_reminder_complete event_id=%s results=%s", reminder_event.id, len(results))
    return results
