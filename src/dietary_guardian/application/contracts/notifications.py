"""Outbound ports for alert and reminder-notification delivery.

Defines the repository/service protocols that application-layer use cases
depend on when enqueueing, dispatching, and tracking notifications.  Concrete
adapters live in ``infrastructure/notifications/`` and
``infrastructure/persistence/``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from dietary_guardian.domain.alerts import AlertMessage, OutboxRecord
from dietary_guardian.domain.notifications import (
    ReminderNotificationEndpoint,
    ReminderNotificationLogEntry,
    ReminderNotificationPreference,
    ScheduledReminderNotification,
)


class AlertRepositoryProtocol(Protocol):
    """Persistence port for alert outbox records."""

    def enqueue_alert(self, message: AlertMessage) -> list[OutboxRecord]: ...

    def lease_alert_records(
        self,
        now: datetime,
        lease_owner: str,
        lease_seconds: int,
        limit: int,
        alert_id: str | None = None,
    ) -> list[OutboxRecord]: ...

    def mark_alert_delivered(self, alert_id: str, sink: str, attempt_count: int | None = None) -> None: ...

    def reschedule_alert(
        self,
        alert_id: str,
        sink: str,
        next_attempt_at: datetime,
        attempt_count: int,
        error: str,
    ) -> None: ...

    def mark_alert_dead_letter(
        self,
        alert_id: str,
        sink: str,
        error: str,
        attempt_count: int | None = None,
    ) -> None: ...

    def list_alert_records(self, alert_id: str | None = None) -> list[OutboxRecord]: ...


class ReminderNotificationRepository(Protocol):
    """Persistence port for scheduled reminder notifications."""

    def list_reminder_notification_preferences(
        self,
        *,
        user_id: str,
        scope_type: str | None = None,
        scope_key: str | None = None,
    ) -> list[ReminderNotificationPreference]: ...

    def save_scheduled_notification(
        self,
        notification: ScheduledReminderNotification,
    ) -> ScheduledReminderNotification: ...

    def append_notification_log(self, entry: ReminderNotificationLogEntry) -> ReminderNotificationLogEntry: ...

    def lease_due_scheduled_notifications(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> list[ScheduledReminderNotification]: ...

    def get_reminder_notification_endpoint(
        self,
        *,
        user_id: str,
        channel: str,
    ) -> ReminderNotificationEndpoint | None: ...

    def enqueue_alert(self, message: AlertMessage) -> list[OutboxRecord]: ...

    def cancel_scheduled_notifications_for_reminder(self, reminder_id: str) -> int: ...

    def list_scheduled_notifications(
        self,
        *,
        reminder_id: str | None = None,
        user_id: str | None = None,
    ) -> list[ScheduledReminderNotification]: ...


class ReminderSchedulerRepository(ReminderNotificationRepository, AlertRepositoryProtocol, Protocol):
    """Combined port required by the reminder scheduler runtime loop."""

    pass


__all__ = [
    "AlertRepositoryProtocol",
    "ReminderNotificationRepository",
    "ReminderSchedulerRepository",
]
