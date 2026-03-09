from __future__ import annotations

from datetime import datetime
from typing import Protocol, TypeAlias

from dietary_guardian.models.alerting import AlertMessage, OutboxRecord
from dietary_guardian.models.reminder_notifications import (
    ReminderNotificationEndpoint,
    ReminderNotificationLogEntry,
    ReminderNotificationPreference,
    ScheduledReminderNotification,
)
from dietary_guardian.services.alerting_service import AlertRepositoryProtocol

from .postgres_app_store import PostgresAppStore
from .sqlite_app_store import SQLiteAppStore

AppStoreBackend: TypeAlias = SQLiteAppStore | PostgresAppStore


class ReminderNotificationRepository(Protocol):
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
    pass
