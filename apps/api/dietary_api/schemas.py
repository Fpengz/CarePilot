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


class AuthSignupRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None
    profile_mode: ProfileMode = "self"


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


class AuthProfileUpdateRequest(BaseModel):
    display_name: str | None = None
    profile_mode: ProfileMode | None = None


class AuthPasswordUpdateRequest(BaseModel):
    current_password: str
    new_password: str


class AuthPasswordUpdateResponse(BaseModel):
    ok: bool = True
    revoked_other_sessions: int


class AuthAuditEvent(BaseModel):
    event_id: str
    event_type: str
    email: EmailStr
    user_id: str | None = None
    created_at: datetime
    metadata: dict[str, object] = Field(default_factory=dict)


class AuthAuditEventListResponse(BaseModel):
    items: list[AuthAuditEvent]


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


class HouseholdCreateRequest(BaseModel):
    name: str


class HouseholdResponse(BaseModel):
    household_id: str
    name: str
    owner_user_id: str
    created_at: datetime


class HouseholdMemberItem(BaseModel):
    user_id: str
    display_name: str
    role: Literal["owner", "member"]
    joined_at: datetime


class HouseholdMembersResponse(BaseModel):
    members: list[HouseholdMemberItem]


class HouseholdBundleResponse(BaseModel):
    household: HouseholdResponse | None
    members: list[HouseholdMemberItem]


class HouseholdInviteResponseItem(BaseModel):
    invite_id: str
    household_id: str
    code: str
    created_by_user_id: str
    created_at: datetime
    expires_at: datetime
    max_uses: int
    uses: int


class HouseholdInviteCreateResponse(BaseModel):
    invite: HouseholdInviteResponseItem


class HouseholdJoinRequest(BaseModel):
    code: str


class HouseholdLeaveResponse(BaseModel):
    ok: bool = True
    left_household_id: str


class HouseholdMemberRemoveResponse(BaseModel):
    ok: bool = True
    removed_user_id: str


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
    summary: dict[str, object]
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
