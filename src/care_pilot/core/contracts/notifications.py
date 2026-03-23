"""Outbound ports for alert and reminder-notification delivery.

Defines the repository/service protocols that application-layer use cases
depend on when enqueueing, dispatching, and tracking notifications.  Concrete
adapters live in ``infrastructure/notifications/`` and
``infrastructure/persistence/``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from care_pilot.features.reminders.domain import (
    MessageEndpoint,
    MessageLogEntry,
    MessagePreference,
    MessageThread,
    MessageThreadMessage,
    MessageThreadParticipant,
    ScheduledMessage,
)
from care_pilot.features.safety.domain.alerts import OutboundMessage, OutboxRecord


class AlertRepositoryProtocol(Protocol):
    """Persistence port for alert outbox records."""

    def enqueue_alert(self, message: OutboundMessage) -> list[OutboxRecord]: ...

    def lease_alert_records(
        self,
        now: datetime,
        lease_owner: str,
        lease_seconds: int,
        limit: int,
        alert_id: str | None = None,
    ) -> list[OutboxRecord]: ...

    def mark_alert_delivered(
        self, alert_id: str, sink: str, attempt_count: int | None = None
    ) -> None: ...

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


class MessageNotificationRepository(Protocol):
    """Persistence port for scheduled message notifications."""

    def list_message_preferences(
        self,
        *,
        user_id: str,
        scope_type: str | None = None,
        scope_key: str | None = None,
    ) -> list[MessagePreference]: ...

    def replace_message_preferences(
        self,
        *,
        user_id: str,
        scope_type: str,
        scope_key: str | None,
        preferences: list[MessagePreference],
    ) -> list[MessagePreference]: ...

    def save_scheduled_notification(
        self,
        notification: ScheduledMessage,
    ) -> ScheduledMessage: ...

    def append_notification_log(self, entry: MessageLogEntry) -> MessageLogEntry: ...

    def lease_due_scheduled_notifications(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> list[ScheduledMessage]: ...

    def get_message_endpoint(
        self,
        *,
        endpoint_id: str,
    ) -> MessageEndpoint | None: ...

    def get_message_endpoint_by_destination(
        self,
        *,
        user_id: str,
        channel: str,
        destination: str,
    ) -> MessageEndpoint | None: ...

    def enqueue_alert(self, message: OutboundMessage) -> list[OutboxRecord]: ...

    def cancel_scheduled_messages_for_reminder(self, reminder_id: str) -> int: ...

    def list_scheduled_notifications(
        self,
        *,
        reminder_id: str | None = None,
        user_id: str | None = None,
    ) -> list[ScheduledMessage]: ...

    def list_message_endpoints(
        self,
        *,
        user_id: str,
    ) -> list[MessageEndpoint]: ...

    def replace_message_endpoints(
        self,
        *,
        user_id: str,
        endpoints: list[MessageEndpoint],
    ) -> list[MessageEndpoint]: ...

    def list_notification_logs(self, *, reminder_id: str) -> list[MessageLogEntry]: ...

    def list_message_logs(self, *, reminder_id: str) -> list[MessageLogEntry]: ...

    def get_message_thread(
        self,
        *,
        user_id: str,
        channel: str,
        endpoint_id: str,
    ) -> MessageThread | None: ...

    def create_message_thread(self, thread: MessageThread) -> MessageThread: ...

    def add_message_thread_participant(
        self,
        participant: MessageThreadParticipant,
    ) -> MessageThreadParticipant: ...

    def append_message_thread_message(self, message: MessageThreadMessage) -> None: ...

    def list_message_thread_messages(self, *, thread_id: str) -> list[MessageThreadMessage]: ...

    def mark_scheduled_notification_dead_letter(
        self,
        notification_id: str,
        *,
        attempt_count: int,
        error: str,
    ) -> None: ...


class ReminderSchedulerRepository(
    MessageNotificationRepository, AlertRepositoryProtocol, Protocol
):
    """Combined port required by the reminder scheduler runtime loop."""

    pass


__all__ = [
    "AlertRepositoryProtocol",
    "MessageNotificationRepository",
    "ReminderSchedulerRepository",
]
