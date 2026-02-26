from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, EmailStr
from dietary_guardian.models.identity import AccountRole, ProfileMode


class ApiError(BaseModel):
    code: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)
    correlation_id: str | None = None


class AuthLoginRequest(BaseModel):
    email: EmailStr
    password: str


class SessionUser(BaseModel):
    user_id: str
    email: EmailStr
    account_role: AccountRole
    scopes: list[str]
    profile_mode: ProfileMode
    display_name: str


class SessionInfo(BaseModel):
    session_id: str
    issued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuthLoginResponse(BaseModel):
    user: SessionUser
    session: SessionInfo


class AuthMeResponse(BaseModel):
    user: SessionUser


class AuthSessionListItem(BaseModel):
    session_id: str
    issued_at: datetime
    is_current: bool


class AuthSessionListResponse(BaseModel):
    sessions: list[AuthSessionListItem]


class AuthSessionRevokeResponse(BaseModel):
    ok: bool = True
    revoked: bool


class AuthSessionRevokeOthersResponse(BaseModel):
    ok: bool = True
    revoked_count: int


class AlertTriggerRequest(BaseModel):
    alert_type: str
    severity: Literal["info", "warning", "critical"]
    message: str
    destinations: list[str]


class AlertTriggerResponse(BaseModel):
    tool_result: dict[str, object]
    outbox_timeline: list[dict[str, object]]
    workflow: dict[str, object]


class AlertTimelineResponse(BaseModel):
    alert_id: str
    outbox_timeline: list[dict[str, object]]


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


class MealAnalyzeResponse(BaseModel):
    vision_result: dict[str, object]
    meal_record: dict[str, object]
    output_envelope: dict[str, object] | None
    workflow: dict[str, object]


class MealRecordsResponse(BaseModel):
    records: list[dict[str, object]]


class WorkflowResponse(BaseModel):
    workflow_name: str
    request_id: str
    correlation_id: str
    replayed: bool
    timeline_events: list[dict[str, object]]


class WorkflowListResponse(BaseModel):
    items: list[dict[str, object]]


class ReportParseRequest(BaseModel):
    source: Literal["pasted_text"] = "pasted_text"
    text: str


class ReportParseResponse(BaseModel):
    readings: list[dict[str, object]]
    snapshot: dict[str, object]


class RecommendationGenerateResponse(BaseModel):
    recommendation: dict[str, object]
    workflow: dict[str, object]


class ReminderGenerateResponse(BaseModel):
    reminders: list[dict[str, object]]
    metrics: dict[str, object]


class ReminderListResponse(BaseModel):
    reminders: list[dict[str, object]]
    metrics: dict[str, object]


class ReminderConfirmRequest(BaseModel):
    confirmed: bool


class ReminderConfirmResponse(BaseModel):
    event: dict[str, object]
    metrics: dict[str, object]
