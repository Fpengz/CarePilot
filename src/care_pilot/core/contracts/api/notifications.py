"""
Define alert and notification API contracts.

This module includes request/response schemas for alert triggers,
notification feeds, and reminder notifications.
"""

from __future__ import annotations

# ruff: noqa: F401
from datetime import date, datetime, timezone
from typing import Literal, TypeAlias

from pydantic import BaseModel, EmailStr, Field, RootModel

from care_pilot.agent.emotion.schemas import (
    EmotionConfidenceBand,
    EmotionLabel,
    EmotionRuntimeHealth,
)
from care_pilot.core.contracts.agent_envelopes import AgentOutputEnvelope
from care_pilot.core.contracts.api.core import JsonValue
from care_pilot.features.companion.core.health.analytics import EngagementMetrics
from care_pilot.features.companion.core.health.models import (
    BiomarkerReading,
    ClinicalProfileSnapshot,
)
from care_pilot.features.meals.domain.models import VisionResult
from care_pilot.features.meals.domain.recognition import MealRecognitionRecord
from care_pilot.features.profiles.domain.models import (
    AccountRole,
    MealScheduleWindow,
    MealSlot,
    ProfileMode,
)
from care_pilot.features.recommendations.domain.models import (
    InteractionEventType,
    RecommendationOutput,
)
from care_pilot.features.reminders.domain.models import ReminderEvent
from care_pilot.features.safety.domain.alerts.models import OutboxState
from care_pilot.platform.observability.tooling.domain.models import ToolExecutionResult


class AlertTriggerRequest(BaseModel):
    alert_type: str
    severity: Literal["info", "warning", "critical"]
    message: str
    destinations: list[str]


class WorkflowTimelineEventPayloadResponse(RootModel[dict[str, JsonValue]]):
    pass


class AlertTimelineItemResponse(BaseModel):
    alert_id: str
    sink: str
    type: str
    severity: Literal["info", "warning", "critical"]
    payload: dict[str, str] = Field(default_factory=dict)
    correlation_id: str
    created_at: datetime
    state: OutboxState
    attempt_count: int
    next_attempt_at: datetime
    last_error: str | None = None
    lease_owner: str | None = None
    lease_until: datetime | None = None
    idempotency_key: str


class NotificationItem(BaseModel):
    id: str
    event_id: str
    event_type: str
    workflow_name: str | None = None
    category: str
    title: str
    message: str
    created_at: datetime
    correlation_id: str
    request_id: str | None = None
    user_id: str | None = None
    read: bool
    severity: Literal["info", "warning", "critical"] = "info"
    action_path: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class NotificationListResponse(BaseModel):
    items: list[NotificationItem]
    unread_count: int


class NotificationMarkReadResponse(BaseModel):
    notification: NotificationItem
    unread_count: int


class NotificationMarkAllReadResponse(BaseModel):
    updated_count: int
    unread_count: int


class MessageAttachment(BaseModel):
    attachment_type: Literal["image", "audio", "file"] = "image"
    url: str
    mime_type: str
    caption: str | None = None
    size_bytes: int | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class MessagePreferenceRuleRequest(BaseModel):
    channel: Literal["in_app", "email", "sms", "push", "telegram", "whatsapp", "wechat"]
    offset_minutes: int = Field(le=0)
    enabled: bool = True


class MessagePreferenceRuleResponse(BaseModel):
    id: str
    scope_type: Literal["default", "reminder_type"]
    scope_key: str | None = None
    channel: Literal["in_app", "email", "sms", "push", "telegram", "whatsapp", "wechat"]
    offset_minutes: int
    enabled: bool
    updated_at: datetime


class MessagePreferenceUpdateRequest(BaseModel):
    rules: list[MessagePreferenceRuleRequest] = Field(default_factory=list)


class MessagePreferenceListResponse(BaseModel):
    preferences: list[MessagePreferenceRuleResponse]


class MessageEndpointRequest(BaseModel):
    channel: Literal["in_app", "email", "sms", "push", "telegram", "whatsapp", "wechat"]
    destination: str
    verified: bool = False


class MessageEndpointResponse(BaseModel):
    id: str
    channel: Literal["in_app", "email", "sms", "push", "telegram", "whatsapp", "wechat"]
    destination: str
    verified: bool
    updated_at: datetime


class MessageEndpointListResponse(BaseModel):
    endpoints: list[MessageEndpointResponse]


class MessageEndpointUpdateRequest(BaseModel):
    endpoints: list[MessageEndpointRequest] = Field(default_factory=list)


class ScheduledMessageItemResponse(BaseModel):
    id: str
    reminder_id: str
    channel: Literal["in_app", "email", "sms", "push", "telegram", "whatsapp", "wechat"]
    trigger_at: datetime
    offset_minutes: int
    status: Literal[
        "pending",
        "queued",
        "processing",
        "retry_scheduled",
        "delivered",
        "dead_letter",
        "cancelled",
    ]
    attempt_count: int
    delivered_at: datetime | None = None
    last_error: str | None = None


class ScheduledMessageListResponse(BaseModel):
    items: list[ScheduledMessageItemResponse]


class MessageLogItemResponse(BaseModel):
    id: str
    scheduled_notification_id: str
    channel: Literal["in_app", "email", "sms", "push", "telegram", "whatsapp", "wechat"]
    attempt_number: int
    event_type: Literal[
        "scheduled",
        "queued",
        "dispatch_started",
        "delivered",
        "retry_scheduled",
        "dead_lettered",
        "cancelled",
    ]
    error_message: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class MessageLogListResponse(BaseModel):
    items: list[MessageLogItemResponse]


ReminderNotificationPreferenceRuleRequest = MessagePreferenceRuleRequest
ReminderNotificationPreferenceRuleResponse = MessagePreferenceRuleResponse
ReminderNotificationPreferenceUpdateRequest = MessagePreferenceUpdateRequest
ReminderNotificationPreferenceListResponse = MessagePreferenceListResponse
ReminderNotificationEndpointRequest = MessageEndpointRequest
ReminderNotificationEndpointResponse = MessageEndpointResponse
ReminderNotificationEndpointListResponse = MessageEndpointListResponse
ReminderNotificationEndpointUpdateRequest = MessageEndpointUpdateRequest
ScheduledReminderNotificationItemResponse = ScheduledMessageItemResponse
ScheduledReminderNotificationListResponse = ScheduledMessageListResponse
ReminderNotificationLogItemResponse = MessageLogItemResponse
ReminderNotificationLogListResponse = MessageLogListResponse
