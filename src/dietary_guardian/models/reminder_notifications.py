"""Compatibility re-export: definitions have moved to dietary_guardian.domain.notifications.models."""
# ruff: noqa: F401
from dietary_guardian.domain.notifications.models import (
    NotificationLogEventType,
    NotificationPreferenceScope,
    QueuedReminderNotification,
    ReminderNotificationChannel,
    ReminderNotificationEndpoint,
    ReminderNotificationLogEntry,
    ReminderNotificationPreference,
    ScheduledNotificationStatus,
    ScheduledReminderNotification,
)
