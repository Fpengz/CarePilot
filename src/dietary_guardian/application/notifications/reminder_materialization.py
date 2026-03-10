"""Reminder notification materialisation, dispatch, and orchestration use cases.

``materialize_reminder_notifications`` converts a ``ReminderEvent`` into one
or more ``ScheduledReminderNotification`` rows (one per user preference / channel).

``dispatch_due_reminder_notifications`` leases rows that are due now, wraps
them as ``AlertMessage`` objects, enqueues them into the alert outbox, and
returns ``QueuedReminderNotification`` receipts.

``cancel_reminder_notifications`` cancels all pending scheduled notifications
for a given reminder and logs the cancellation.

The CRUD orchestration functions (``list_notification_preferences``,
``replace_notification_preferences``, ``list_reminder_notification_schedules``,
``list_notification_endpoints``, ``replace_notification_endpoints``,
``list_reminder_notification_logs``) manage user-facing preference and endpoint
records via ``AppContext``.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, cast
from uuid import uuid4

from dietary_guardian.application.contracts.notifications import ReminderNotificationRepository
from dietary_guardian.domain.alerts import AlertMessage
from dietary_guardian.domain.notifications import ReminderEvent
from dietary_guardian.domain.notifications.models import (
    NotificationPreferenceScope,
    QueuedReminderNotification,
    ReminderNotificationEndpoint,
    ReminderNotificationLogEntry,
    ReminderNotificationPreference,
    ScheduledReminderNotification,
)
from dietary_guardian.infrastructure.persistence import AppStoreBackend
from dietary_guardian.infrastructure.observability import get_logger

if TYPE_CHECKING:
    from apps.api.dietary_api.deps import AppContext

from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas import (
    ReminderNotificationEndpointListResponse,
    ReminderNotificationEndpointRequest,
    ReminderNotificationEndpointResponse,
    ReminderNotificationLogItemResponse,
    ReminderNotificationLogListResponse,
    ReminderNotificationPreferenceListResponse,
    ReminderNotificationPreferenceRuleRequest,
    ReminderNotificationPreferenceRuleResponse,
    ScheduledReminderNotificationItemResponse,
    ScheduledReminderNotificationListResponse,
)

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
    "list_notification_endpoints",
    "list_notification_preferences",
    "list_reminder_notification_logs",
    "list_reminder_notification_schedules",
    "materialize_reminder_notifications",
    "replace_notification_endpoints",
    "replace_notification_preferences",
    "resolve_notification_preferences",
]

# ---------------------------------------------------------------------------
# Preference / endpoint / log CRUD orchestration (moved from services layer)
# ---------------------------------------------------------------------------


def list_notification_preferences(
    *,
    context: "AppContext",
    user_id: str,
    scope_type: str | None = None,
    scope_key: str | None = None,
) -> ReminderNotificationPreferenceListResponse:
    items = context.stores.reminders.list_reminder_notification_preferences(
        user_id=user_id,
        scope_type=scope_type,
        scope_key=scope_key,
    )
    return ReminderNotificationPreferenceListResponse(
        preferences=[
            ReminderNotificationPreferenceRuleResponse(
                id=item.id,
                scope_type=item.scope_type,
                scope_key=item.scope_key,
                channel=item.channel,
                offset_minutes=item.offset_minutes,
                enabled=item.enabled,
                updated_at=item.updated_at,
            )
            for item in items
        ]
    )


def replace_notification_preferences(
    *,
    context: "AppContext",
    user_id: str,
    scope_type: str,
    scope_key: str | None,
    rules: list[ReminderNotificationPreferenceRuleRequest],
) -> ReminderNotificationPreferenceListResponse:
    seen: set[tuple[str, int]] = set()
    now = datetime.now(timezone.utc)
    preferences: list[ReminderNotificationPreference] = []
    for rule in rules:
        key = (rule.channel, rule.offset_minutes)
        if key in seen:
            raise build_api_error(
                status_code=400,
                code="reminders.notification_preferences.invalid",
                message="duplicate notification preference rule",
            )
        seen.add(key)
        preferences.append(
            ReminderNotificationPreference(
                id=str(uuid4()),
                user_id=user_id,
                scope_type=cast(NotificationPreferenceScope, scope_type),
                scope_key=scope_key,
                channel=rule.channel,
                offset_minutes=rule.offset_minutes,
                enabled=rule.enabled,
                created_at=now,
                updated_at=now,
            )
        )
    saved = context.stores.reminders.replace_reminder_notification_preferences(
        user_id=user_id,
        scope_type=scope_type,
        scope_key=scope_key,
        preferences=preferences,
    )
    return ReminderNotificationPreferenceListResponse(
        preferences=[
            ReminderNotificationPreferenceRuleResponse(
                id=item.id,
                scope_type=item.scope_type,
                scope_key=item.scope_key,
                channel=item.channel,
                offset_minutes=item.offset_minutes,
                enabled=item.enabled,
                updated_at=item.updated_at,
            )
            for item in saved
        ]
    )


def list_reminder_notification_schedules(
    *,
    context: "AppContext",
    user_id: str,
    reminder_id: str,
) -> ScheduledReminderNotificationListResponse:
    reminder = context.stores.reminders.get_reminder_event(reminder_id)
    if reminder is None or reminder.user_id != user_id:
        raise build_api_error(status_code=404, code="reminders.not_found", message="reminder not found")
    items = context.stores.reminders.list_scheduled_notifications(reminder_id=reminder_id)
    return ScheduledReminderNotificationListResponse(
        items=[
            ScheduledReminderNotificationItemResponse(
                id=item.id,
                reminder_id=item.reminder_id,
                channel=item.channel,
                trigger_at=item.trigger_at,
                offset_minutes=item.offset_minutes,
                status=item.status,
                attempt_count=item.attempt_count,
                delivered_at=item.delivered_at,
                last_error=item.last_error,
            )
            for item in items
        ]
    )


def list_notification_endpoints(*, context: "AppContext", user_id: str) -> ReminderNotificationEndpointListResponse:
    items = context.stores.reminders.list_reminder_notification_endpoints(user_id=user_id)
    return ReminderNotificationEndpointListResponse(
        endpoints=[
            ReminderNotificationEndpointResponse(
                id=item.id,
                channel=item.channel,
                destination=item.destination,
                verified=item.verified,
                updated_at=item.updated_at,
            )
            for item in items
        ]
    )


def replace_notification_endpoints(
    *,
    context: "AppContext",
    user_id: str,
    endpoints: list[ReminderNotificationEndpointRequest],
) -> ReminderNotificationEndpointListResponse:
    seen: set[str] = set()
    now = datetime.now(timezone.utc)
    rows: list[ReminderNotificationEndpoint] = []
    for endpoint in endpoints:
        if endpoint.channel in seen:
            raise build_api_error(
                status_code=400,
                code="reminders.notification_endpoints.invalid",
                message="duplicate notification endpoint channel",
            )
        seen.add(endpoint.channel)
        rows.append(
            ReminderNotificationEndpoint(
                id=str(uuid4()),
                user_id=user_id,
                channel=endpoint.channel,
                destination=endpoint.destination.strip(),
                verified=endpoint.verified,
                created_at=now,
                updated_at=now,
            )
        )
    saved = context.stores.reminders.replace_reminder_notification_endpoints(user_id=user_id, endpoints=rows)
    return ReminderNotificationEndpointListResponse(
        endpoints=[
            ReminderNotificationEndpointResponse(
                id=item.id,
                channel=item.channel,
                destination=item.destination,
                verified=item.verified,
                updated_at=item.updated_at,
            )
            for item in saved
        ]
    )


def list_reminder_notification_logs(
    *,
    context: "AppContext",
    user_id: str,
    reminder_id: str,
) -> ReminderNotificationLogListResponse:
    reminder = context.stores.reminders.get_reminder_event(reminder_id)
    if reminder is None or reminder.user_id != user_id:
        raise build_api_error(status_code=404, code="reminders.not_found", message="reminder not found")
    items = context.stores.reminders.list_notification_logs(reminder_id=reminder_id)
    return ReminderNotificationLogListResponse(
        items=[
            ReminderNotificationLogItemResponse(
                id=item.id,
                scheduled_notification_id=item.scheduled_notification_id,
                channel=item.channel,
                attempt_number=item.attempt_number,
                event_type=item.event_type,
                error_message=item.error_message,
                metadata=item.metadata,
                created_at=item.created_at,
            )
            for item in items
        ]
    )
