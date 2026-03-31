"""Define reminder domain models."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from care_pilot.config.app import get_settings
from care_pilot.features.profiles.domain.models import MealSlot


class MobilityReminderSettings(BaseModel):
    user_id: str
    enabled: bool = False
    interval_minutes: int = 120
    active_start_time: str = "08:00"
    active_end_time: str = "20:00"
    updated_at: str | None = None


MessageChannel = Literal[
    "in_app",
    "chat",
    "email",
    "sms",
    "push",
    "telegram",
    "whatsapp",
    "wechat",
]
ReminderNotificationChannel = MessageChannel
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

class MessageAttachment(BaseModel):
    attachment_type: Literal["image", "audio", "file"] = "image"
    url: str
    mime_type: str
    caption: str | None = None
    size_bytes: int | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class MessageEndpoint(BaseModel):
    id: str
    user_id: str
    channel: MessageChannel
    destination: str
    verified: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MessagePreference(BaseModel):
    id: str
    user_id: str
    scope_type: NotificationPreferenceScope = "default"
    scope_key: str | None = None
    channel: MessageChannel
    offset_minutes: int = 0
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ScheduledMessage(BaseModel):
    id: str
    reminder_id: str
    user_id: str
    channel: MessageChannel
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class QueuedMessage(BaseModel):
    scheduled_notification_id: str
    reminder_id: str
    channel: MessageChannel
    queued_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MessageLogEntry(BaseModel):
    id: str
    scheduled_notification_id: str
    reminder_id: str
    user_id: str
    channel: MessageChannel
    attempt_number: int = 0
    event_type: NotificationLogEventType
    error_message: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MessageThread(BaseModel):
    id: str
    user_id: str
    channel: MessageChannel
    endpoint_id: str
    status: Literal["active", "archived"] = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MessageThreadParticipant(BaseModel):
    id: str
    thread_id: str
    participant_type: Literal["user", "assistant", "system"] = "user"
    participant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MessageThreadMessage(BaseModel):
    id: str
    thread_id: str
    user_id: str
    channel: MessageChannel
    direction: Literal["inbound", "outbound"] = "inbound"
    body: str
    attachments: list[MessageAttachment] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


ReminderNotificationEndpoint = MessageEndpoint
ReminderNotificationPreference = MessagePreference
ScheduledReminderNotification = ScheduledMessage
QueuedReminderNotification = QueuedMessage
ReminderNotificationLogEntry = MessageLogEntry


TimingType = Literal["pre_meal", "post_meal", "fixed_time"]
FrequencyType = Literal["times_per_day", "fixed_slots", "fixed_time"]
ReminderStatus = Literal["sent", "acknowledged", "missed"]
MealConfirmation = Literal["yes", "no", "unknown"]
ReminderType = Literal["medication", "mobility"]
MedicationSourceType = Literal["manual", "plain_text", "upload"]
ReminderSourceType = Literal[
    "manual",
    "plain_text",
    "upload",
    "clinician",
    "admin",
    "agent_suggested_confirmed",
]
ReminderSchedulePattern = Literal[
    "one_time",
    "daily_fixed_times",
    "multiple_times_per_day",
    "every_x_hours",
    "specific_weekdays",
    "meal_relative",
    "bedtime",
    "prn",
    "temporary_course",
]
ReminderOccurrenceStatus = Literal[
    "scheduled",
    "queued",
    "processing",
    "completed",
    "skipped",
    "snoozed",
    "missed",
    "cancelled",
]
ReminderActionType = Literal[
    "taken",
    "skipped",
    "snooze",
    "view_details",
    "ignored",
    "expired",
]
ReminderActionOutcome = Literal["on_time", "late", "missed", "info"]


class ReminderScheduleRule(BaseModel):
    pattern: ReminderSchedulePattern
    times: list[str] = Field(default_factory=list)
    interval_hours: int | None = None
    weekdays: list[int] = Field(default_factory=list)
    meal_slot: MealSlot | None = None
    relative_direction: Literal["before", "after"] | None = None
    offset_minutes: int = 0
    timezone: str = Field(default_factory=lambda: get_settings().app.timezone)
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = None
    max_daily_occurrences: int | None = None
    as_needed: bool = False
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    pause_until: datetime | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ReminderDefinition(BaseModel):
    id: str
    user_id: str
    regimen_id: str | None = None
    reminder_type: ReminderType = "medication"
    source: ReminderSourceType = "manual"
    title: str
    body: str | None = None
    medication_name: str = ""
    dosage_text: str = ""
    route: str | None = None
    instructions_text: str | None = None
    special_notes: str | None = None
    treatment_duration: str | None = None
    channels: list[MessageChannel] = Field(default_factory=lambda: ["in_app"])
    timezone: str = Field(default_factory=lambda: get_settings().app.timezone)
    schedule: ReminderScheduleRule
    active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReminderOccurrence(BaseModel):
    id: str
    reminder_definition_id: str
    user_id: str
    scheduled_for: datetime
    trigger_at: datetime
    status: ReminderOccurrenceStatus = "scheduled"
    action: ReminderActionType | None = None
    action_outcome: ReminderActionOutcome | None = None
    acted_at: datetime | None = None
    grace_window_minutes: int = 60
    retry_count: int = 0
    last_delivery_status: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReminderActionRecord(BaseModel):
    id: str
    occurrence_id: str
    reminder_definition_id: str
    user_id: str
    action: ReminderActionType
    acted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    snooze_minutes: int | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ReminderDeliveryAttempt(BaseModel):
    id: str
    occurrence_id: str
    reminder_definition_id: str
    user_id: str
    channel: ReminderNotificationChannel
    scheduled_for: datetime
    triggered_at: datetime
    delivery_status: ScheduledNotificationStatus
    error_message: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class MedicationRegimen(BaseModel):
    id: str
    user_id: str
    medication_name: str
    canonical_name: str | None = None
    dosage_text: str
    timing_type: TimingType
    frequency_type: FrequencyType = "fixed_time"
    frequency_times_per_day: int = 1
    time_rules: list[dict[str, object]] = Field(default_factory=list)
    offset_minutes: int = 0
    slot_scope: list[MealSlot] = Field(default_factory=list)
    fixed_time: str | None = None
    max_daily_doses: int = 1
    instructions_text: str | None = None
    source_type: MedicationSourceType = "manual"
    source_filename: str | None = None
    source_hash: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    timezone: str = Field(default_factory=lambda: get_settings().app.timezone)
    parse_confidence: float | None = None
    active: bool = True


class ReminderEvent(BaseModel):
    id: str
    user_id: str
    reminder_definition_id: str | None = None
    occurrence_id: str | None = None
    regimen_id: str | None = None
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
