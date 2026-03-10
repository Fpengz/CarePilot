"""Reminder notification materialisation and dispatch use cases.

``materialize_reminder_notifications`` converts a ``ReminderEvent`` into one
or more ``ScheduledReminderNotification`` rows (one per user preference / channel).

``dispatch_due_reminder_notifications`` leases rows that are due now, wraps
them as ``AlertMessage`` objects, enqueues them into the alert outbox, and
returns ``QueuedReminderNotification`` receipts.

``cancel_reminder_notifications`` cancels all pending scheduled notifications
for a given reminder and logs the cancellation.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from dietary_guardian.application.contracts.notifications import ReminderNotificationRepository
from dietary_guardian.domain.alerts import AlertMessage
from dietary_guardian.domain.notifications import ReminderEvent
from dietary_guardian.domain.notifications.models import (
    QueuedReminderNotification,
    ReminderNotificationLogEntry,
    ReminderNotificationPreference,
    ScheduledReminderNotification,
)
from dietary_guardian.infrastructure.persistence import AppStoreBackend
from dietary_guardian.logging_config import get_logger

logger = get_logger(__name__)

SYSTEM_DEFAULT_CHANNEL = "in_app"
SYSTEM_DEFAULT_OFFSET_MINUTES = 0


def resolve_notification_preferences(
    *,
    repository: ReminderNotificationRepository | AppStoreBackend,
    user_id: str,
    reminder_type: str,
) -> list[ReminderNotificationPreference]:
    """Return the effective preferences for a user/reminder-type combination.

    Falls back to default-scoped preferences, then to a hard-coded in-app
    system default if neither is configured.
    """
    typed = repository.list_reminder_notification_preferences(
        user_id=user_id,
        scope_type="reminder_type",
        scope_key=reminder_type,
    )
    enabled_typed = [item for item in typed if item.enabled]
    if enabled_typed:
        return enabled_typed
    defaults = repository.list_reminder_notification_preferences(
        user_id=user_id,
        scope_type="default",
        scope_key=None,
    )
    enabled_defaults = [item for item in defaults if item.enabled]
    if enabled_defaults:
        return enabled_defaults
    now = datetime.now(timezone.utc)
    return [
        ReminderNotificationPreference(
            id=f"system-default-{user_id}",
            user_id=user_id,
            scope_type="default",
            scope_key=None,
            channel=SYSTEM_DEFAULT_CHANNEL,
            offset_minutes=SYSTEM_DEFAULT_OFFSET_MINUTES,
            enabled=True,
            created_at=now,
            updated_at=now,
        )
    ]


def _build_idempotency_key(*, reminder_id: str, channel: str, trigger_at: datetime, offset_minutes: int) -> str:
    raw = f"{reminder_id}:{channel}:{trigger_at.isoformat()}:{offset_minutes}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def materialize_reminder_notifications(
    *,
    repository: ReminderNotificationRepository | AppStoreBackend,
    reminder_event: ReminderEvent,
    reminder_type: str,
) -> list[ScheduledReminderNotification]:
    """Create ``ScheduledReminderNotification`` rows for each applicable preference."""
    preferences = resolve_notification_preferences(
        repository=repository,
        user_id=reminder_event.user_id,
        reminder_type=reminder_type,
    )
    created: list[ScheduledReminderNotification] = []
    for preference in preferences:
        trigger_at = reminder_event.scheduled_at + timedelta(minutes=preference.offset_minutes)
        now = datetime.now(timezone.utc)
        scheduled = ScheduledReminderNotification(
            id=str(uuid4()),
            reminder_id=reminder_event.id,
            user_id=reminder_event.user_id,
            channel=preference.channel,
            trigger_at=trigger_at,
            offset_minutes=preference.offset_minutes,
            preference_id=preference.id if not preference.id.startswith("system-default-") else None,
            status="pending",
            attempt_count=0,
            next_attempt_at=trigger_at,
            payload={
                "reminder_id": reminder_event.id,
                "reminder_type": reminder_event.reminder_type,
                "title": reminder_event.title,
                "body": reminder_event.body,
                "medication_name": reminder_event.medication_name,
                "dosage_text": reminder_event.dosage_text,
                "scheduled_at": reminder_event.scheduled_at.isoformat(),
                "slot": reminder_event.slot,
                "user_id": reminder_event.user_id,
            },
            idempotency_key=_build_idempotency_key(
                reminder_id=reminder_event.id,
                channel=preference.channel,
                trigger_at=trigger_at,
                offset_minutes=preference.offset_minutes,
            ),
            created_at=now,
            updated_at=now,
        )
        persisted = repository.save_scheduled_notification(scheduled)
        created.append(persisted)
        repository.append_notification_log(
            ReminderNotificationLogEntry(
                id=str(uuid4()),
                scheduled_notification_id=persisted.id,
                reminder_id=reminder_event.id,
                user_id=reminder_event.user_id,
                channel=persisted.channel,
                event_type="scheduled",
                metadata={"trigger_at": persisted.trigger_at.isoformat()},
            )
        )
    logger.info(
        "materialize_reminder_notifications reminder_id=%s user_id=%s created=%s",
        reminder_event.id,
        reminder_event.user_id,
        len(created),
    )
    return created


def dispatch_due_reminder_notifications(
    *,
    repository: ReminderNotificationRepository | AppStoreBackend,
    now: datetime | None = None,
    limit: int = 100,
) -> list[QueuedReminderNotification]:
    """Lease due scheduled notifications and enqueue them into the alert outbox."""
    dispatch_at = now or datetime.now(timezone.utc)
    due_items = repository.lease_due_scheduled_notifications(now=dispatch_at, limit=limit)
    if not due_items:
        return []

    queued: list[QueuedReminderNotification] = []
    for item in due_items:
        endpoint = repository.get_reminder_notification_endpoint(user_id=item.user_id, channel=item.channel)
        message = AlertMessage(
            alert_id=item.id,
            type="reminder_notification",
            severity="info",
            payload={
                "scheduled_notification_id": item.id,
                "reminder_id": item.reminder_id,
                "user_id": item.user_id,
                "channel": item.channel,
                "reminder_type": str(item.payload.get("reminder_type", "medication")),
                "title": str(item.payload.get("title", "")),
                "body": str(item.payload.get("body", "")),
                "medication_name": str(item.payload.get("medication_name", "")),
                "dosage_text": str(item.payload.get("dosage_text", "")),
                "scheduled_at": str(item.payload.get("scheduled_at", "")),
                "trigger_at": item.trigger_at.isoformat(),
                "destination": endpoint.destination if endpoint is not None else "",
                "destination_verified": "true" if endpoint and endpoint.verified else "false",
            },
            destinations=[item.channel],
            correlation_id=item.id,
            created_at=dispatch_at,
        )
        repository.enqueue_alert(message)
        repository.append_notification_log(
            ReminderNotificationLogEntry(
                id=str(uuid4()),
                scheduled_notification_id=item.id,
                reminder_id=item.reminder_id,
                user_id=item.user_id,
                channel=item.channel,
                event_type="queued",
                metadata={"trigger_at": item.trigger_at.isoformat()},
            )
        )
        queued.append(
            QueuedReminderNotification(
                scheduled_notification_id=item.id,
                reminder_id=item.reminder_id,
                channel=item.channel,
                queued_at=dispatch_at,
            )
        )
    logger.info("dispatch_due_reminder_notifications queued=%s", len(queued))
    return queued


def cancel_reminder_notifications(
    *,
    repository: ReminderNotificationRepository | AppStoreBackend,
    reminder_id: str,
) -> int:
    """Cancel all pending scheduled notifications for a reminder and log the event."""
    count = repository.cancel_scheduled_notifications_for_reminder(reminder_id)
    for item in repository.list_scheduled_notifications(reminder_id=reminder_id):
        if item.status != "cancelled":
            continue
        repository.append_notification_log(
            ReminderNotificationLogEntry(
                id=str(uuid4()),
                scheduled_notification_id=item.id,
                reminder_id=item.reminder_id,
                user_id=item.user_id,
                channel=item.channel,
                attempt_number=item.attempt_count,
                event_type="cancelled",
            )
        )
    return count


__all__ = [
    "cancel_reminder_notifications",
    "dispatch_due_reminder_notifications",
    "materialize_reminder_notifications",
    "resolve_notification_preferences",
]
