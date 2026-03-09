"""API orchestration for reminder notification preferences, endpoints, and logs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import cast
from uuid import uuid4

from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas import (
    ReminderNotificationEndpointListResponse,
    ReminderNotificationEndpointRequest,
    ReminderNotificationEndpointResponse,
    ReminderNotificationLogItemResponse,
    ReminderNotificationLogListResponse,
    ReminderNotificationPreferenceListResponse,
    ReminderNotificationPreferenceRuleResponse,
    ReminderNotificationPreferenceRuleRequest,
    ScheduledReminderNotificationItemResponse,
    ScheduledReminderNotificationListResponse,
)
from dietary_guardian.models.reminder_notifications import (
    NotificationPreferenceScope,
    ReminderNotificationEndpoint,
    ReminderNotificationPreference,
)


def list_notification_preferences(
    *,
    context: AppContext,
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
    context: AppContext,
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
    context: AppContext,
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


def list_notification_endpoints(*, context: AppContext, user_id: str) -> ReminderNotificationEndpointListResponse:
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
    context: AppContext,
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
    context: AppContext,
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
