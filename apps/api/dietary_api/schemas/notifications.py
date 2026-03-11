"""Alert trigger, notification, and reminder-notification API contracts."""

from __future__ import annotations

# ruff: noqa: F401
from datetime import date, datetime, timezone
from typing import Literal, TypeAlias

from pydantic import BaseModel, EmailStr, Field, RootModel

from dietary_guardian.domain.alerts.models import OutboxState
from dietary_guardian.domain.health.models import (
    BiomarkerReading,
    ClinicalProfileSnapshot,
)
from dietary_guardian.domain.identity.models import (
    AccountRole,
    MealScheduleWindow,
    MealSlot,
    ProfileMode,
)
from dietary_guardian.domain.notifications.models import ReminderEvent
from dietary_guardian.domain.recommendations.models import (
    InteractionEventType,
    RecommendationOutput,
)
from dietary_guardian.domain.health.analytics import EngagementMetrics
from dietary_guardian.application.contracts.agent_envelopes import AgentOutputEnvelope
from dietary_guardian.domain.health.emotion import (
    EmotionConfidenceBand,
    EmotionLabel,
    EmotionRuntimeHealth,
)
from dietary_guardian.domain.meals.models import VisionResult
from dietary_guardian.domain.meals.recognition import MealRecognitionRecord
from dietary_guardian.domain.tooling.models import ToolExecutionResult

from .core import JsonValue


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


class ReminderNotificationPreferenceRuleRequest(BaseModel):
    channel: Literal["in_app", "email", "sms", "push", "telegram", "whatsapp", "wechat"]
    offset_minutes: int = Field(le=0)
    enabled: bool = True


class ReminderNotificationPreferenceRuleResponse(BaseModel):
    id: str
    scope_type: Literal["default", "reminder_type"]
    scope_key: str | None = None
    channel: Literal["in_app", "email", "sms", "push", "telegram", "whatsapp", "wechat"]
    offset_minutes: int
    enabled: bool
    updated_at: datetime


class ReminderNotificationPreferenceUpdateRequest(BaseModel):
    rules: list[ReminderNotificationPreferenceRuleRequest] = Field(default_factory=list)


class ReminderNotificationPreferenceListResponse(BaseModel):
    preferences: list[ReminderNotificationPreferenceRuleResponse]


class ReminderNotificationEndpointRequest(BaseModel):
    channel: Literal["in_app", "email", "sms", "push", "telegram", "whatsapp", "wechat"]
    destination: str
    verified: bool = False


class ReminderNotificationEndpointResponse(BaseModel):
    id: str
    channel: Literal["in_app", "email", "sms", "push", "telegram", "whatsapp", "wechat"]
    destination: str
    verified: bool
    updated_at: datetime


class ReminderNotificationEndpointListResponse(BaseModel):
    endpoints: list[ReminderNotificationEndpointResponse]


class ReminderNotificationEndpointUpdateRequest(BaseModel):
    endpoints: list[ReminderNotificationEndpointRequest] = Field(default_factory=list)


class ScheduledReminderNotificationItemResponse(BaseModel):
    id: str
    reminder_id: str
    channel: Literal["in_app", "email", "sms", "push", "telegram", "whatsapp", "wechat"]
    trigger_at: datetime
    offset_minutes: int
    status: Literal["pending", "queued", "processing", "retry_scheduled", "delivered", "dead_letter", "cancelled"]
    attempt_count: int
    delivered_at: datetime | None = None
    last_error: str | None = None


class ScheduledReminderNotificationListResponse(BaseModel):
    items: list[ScheduledReminderNotificationItemResponse]


class ReminderNotificationLogItemResponse(BaseModel):
    id: str
    scheduled_notification_id: str
    channel: Literal["in_app", "email", "sms", "push", "telegram", "whatsapp", "wechat"]
    attempt_number: int
    event_type: Literal["scheduled", "queued", "dispatch_started", "delivered", "retry_scheduled", "dead_lettered", "cancelled"]
    error_message: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class ReminderNotificationLogListResponse(BaseModel):
    items: list[ReminderNotificationLogItemResponse]

