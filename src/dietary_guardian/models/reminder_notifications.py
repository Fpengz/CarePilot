from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


ReminderNotificationChannel = Literal[
    "in_app",
    "email",
    "sms",
    "push",
    "telegram",
    "whatsapp",
    "wechat",
]
NotificationPreferenceScope = Literal["default", "reminder_type"]
ScheduledNotificationStatus = Literal[
    "pending",
    "queued",
    "processing",
    "retry_scheduled",
    "delivered",
    "dead_letter",
    "cancelled",
]
NotificationLogEventType = Literal[
    "scheduled",
    "queued",
    "dispatch_started",
    "delivered",
    "retry_scheduled",
    "dead_lettered",
    "cancelled",
]


class ReminderNotificationEndpoint(BaseModel):
    id: str
    user_id: str
    channel: ReminderNotificationChannel
    destination: str
    verified: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReminderNotificationPreference(BaseModel):
    id: str
    user_id: str
    scope_type: NotificationPreferenceScope = "default"
    scope_key: str | None = None
    channel: ReminderNotificationChannel
    offset_minutes: int = 0
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScheduledReminderNotification(BaseModel):
    id: str
    reminder_id: str
    user_id: str
    channel: ReminderNotificationChannel
    trigger_at: datetime
    offset_minutes: int = 0
    preference_id: str | None = None
    status: ScheduledNotificationStatus = "pending"
    attempt_count: int = 0
    next_attempt_at: datetime | None = None
    queued_at: datetime | None = None
    delivered_at: datetime | None = None
    last_error: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)
    idempotency_key: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReminderNotificationLogEntry(BaseModel):
    id: str
    scheduled_notification_id: str
    reminder_id: str
    user_id: str
    channel: ReminderNotificationChannel
    attempt_number: int = 0
    event_type: NotificationLogEventType
    error_message: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QueuedReminderNotification(BaseModel):
    scheduled_notification_id: str
    reminder_id: str
    channel: ReminderNotificationChannel
    queued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
