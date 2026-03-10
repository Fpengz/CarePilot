"""Domain model definitions for the notifications subdomain: medication regimens, reminders, and mobility settings."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from dietary_guardian.domain.identity.models import MealSlot


class MobilityReminderSettings(BaseModel):
    user_id: str
    enabled: bool = False
    interval_minutes: int = 120
    active_start_time: str = "08:00"
    active_end_time: str = "20:00"
    updated_at: str | None = None


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
    payload: dict[str, object] = Field(default_factory=dict)
    idempotency_key: str
    last_error: str | None = None
    delivered_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QueuedReminderNotification(BaseModel):
    scheduled_notification_id: str
    reminder_id: str
    channel: ReminderNotificationChannel
    queued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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


TimingType = Literal["pre_meal", "post_meal", "fixed_time"]
ReminderStatus = Literal["sent", "acknowledged", "missed"]
MealConfirmation = Literal["yes", "no", "unknown"]
ReminderType = Literal["medication", "mobility"]


class MedicationRegimen(BaseModel):
    id: str
    user_id: str
    medication_name: str
    dosage_text: str
    timing_type: TimingType
    offset_minutes: int = 0
    slot_scope: list[MealSlot] = Field(default_factory=list)
    fixed_time: str | None = None
    max_daily_doses: int = 1
    active: bool = True


class ReminderEvent(BaseModel):
    id: str
    user_id: str
    reminder_type: ReminderType = "medication"
    title: str = "Medication Reminder"
    body: str | None = None
    medication_name: str = ""
    scheduled_at: datetime
    slot: MealSlot | None = None
    dosage_text: str = ""
    status: ReminderStatus = "sent"
    meal_confirmation: MealConfirmation = "unknown"
    sent_at: datetime | None = None
    ack_at: datetime | None = None
