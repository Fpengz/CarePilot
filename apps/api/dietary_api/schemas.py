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


class HealthProfileCondition(BaseModel):
    name: str
    severity: str


class HealthProfileMedication(BaseModel):
    name: str
    dosage: str
    contraindications: list[str] = Field(default_factory=list)


class HealthProfileCompletenessResponse(BaseModel):
    state: Literal["needs_profile", "partial", "ready"]
    missing_fields: list[str] = Field(default_factory=list)


class HealthProfileResponseItem(BaseModel):
    age: int | None = None
    locale: str
    height_cm: float | None = None
    weight_kg: float | None = None
    bmi: float | None = None
    daily_sodium_limit_mg: float
    daily_sugar_limit_g: float
    target_calories_per_day: float | None = None
    macro_focus: list[str] = Field(default_factory=list)
    conditions: list[HealthProfileCondition] = Field(default_factory=list)
    medications: list[HealthProfileMedication] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    nutrition_goals: list[str] = Field(default_factory=list)
    preferred_cuisines: list[str] = Field(default_factory=list)
    disliked_ingredients: list[str] = Field(default_factory=list)
    budget_tier: Literal["budget", "moderate", "flexible"] = "moderate"
    fallback_mode: bool = False
    completeness: HealthProfileCompletenessResponse
    updated_at: datetime | None = None


class HealthProfileUpdateRequest(BaseModel):
    age: int | None = Field(default=None, ge=0, le=130)
    locale: str | None = None
    height_cm: float | None = Field(default=None, gt=0)
    weight_kg: float | None = Field(default=None, gt=0)
    daily_sodium_limit_mg: float | None = Field(default=None, gt=0)
    daily_sugar_limit_g: float | None = Field(default=None, gt=0)
    target_calories_per_day: float | None = Field(default=None, gt=0)
    macro_focus: list[str] | None = None
    conditions: list[HealthProfileCondition] | None = None
    medications: list[HealthProfileMedication] | None = None
    allergies: list[str] | None = None
    nutrition_goals: list[str] | None = None
    preferred_cuisines: list[str] | None = None
    disliked_ingredients: list[str] | None = None
    budget_tier: Literal["budget", "moderate", "flexible"] | None = None


class HealthProfileEnvelopeResponse(BaseModel):
    profile: HealthProfileResponseItem


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


class HouseholdUpdateRequest(BaseModel):
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
    active_household_id: str | None = None


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


class HouseholdActiveUpdateRequest(BaseModel):
    household_id: str | None


class HouseholdActiveUpdateResponse(BaseModel):
    ok: bool = True
    active_household_id: str | None = None


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


class MealAnalyzeResponse(BaseModel):
    summary: dict[str, object]
    vision_result: dict[str, object]
    meal_record: dict[str, object]
    output_envelope: dict[str, object] | None
    workflow: dict[str, object]


class MealRecordsResponse(BaseModel):
    records: list[dict[str, object]]
    page: dict[str, object] | None = None


class WorkflowResponse(BaseModel):
    workflow_name: str
    request_id: str
    correlation_id: str
    replayed: bool
    timeline_events: list[dict[str, object]]


class WorkflowListItem(BaseModel):
    correlation_id: str
    request_id: str | None = None
    user_id: str | None = None
    workflow_name: str | None = None
    created_at: datetime
    latest_event_at: datetime
    event_count: int


class WorkflowListResponse(BaseModel):
    items: list[WorkflowListItem]


class ReportParseRequest(BaseModel):
    source: Literal["pasted_text"] = "pasted_text"
    text: str


class ReportParseResponse(BaseModel):
    readings: list[dict[str, object]]
    snapshot: dict[str, object]


class RecommendationGenerateResponse(BaseModel):
    recommendation: dict[str, object]
    workflow: dict[str, object]


class SuggestionGenerateFromReportRequest(BaseModel):
    source: Literal["pasted_text"] = "pasted_text"
    text: str


class SafetyDecisionResponse(BaseModel):
    decision: Literal["allow", "modify", "refuse", "escalate", "ask_clarification"]
    reasons: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    redactions: list[str] = Field(default_factory=list)


class SuggestionItemResponse(BaseModel):
    suggestion_id: str
    created_at: datetime
    source_user_id: str
    source_display_name: str
    disclaimer: str
    safety: SafetyDecisionResponse
    report_parse: dict[str, object]
    recommendation: dict[str, object]
    workflow: dict[str, object]


class SuggestionGenerateFromReportResponse(BaseModel):
    suggestion: SuggestionItemResponse


class DailySuggestionCardResponse(BaseModel):
    slot: Literal["breakfast", "lunch", "dinner", "snack"]
    title: str
    venue_type: str
    why_it_fits: list[str] = Field(default_factory=list)
    caution_notes: list[str] = Field(default_factory=list)
    confidence: float


class DailySuggestionBundleResponse(BaseModel):
    locale: str
    generated_at: datetime
    data_sources: dict[str, object] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    suggestions: dict[str, DailySuggestionCardResponse]


class DailySuggestionsResponse(BaseModel):
    profile: HealthProfileResponseItem
    bundle: DailySuggestionBundleResponse


class RecommendationInteractionRequest(BaseModel):
    recommendation_id: str
    candidate_id: str
    event_type: Literal["viewed", "accepted", "dismissed", "swap_selected", "meal_logged_after_recommendation", "ignored"]
    slot: Literal["breakfast", "lunch", "dinner", "snack"]
    source_meal_id: str | None = None
    selected_meal_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class RecommendationInteractionResponse(BaseModel):
    ok: bool = True
    interaction: dict[str, object]
    preference_snapshot: dict[str, object]


class RecommendationSubstitutionRequest(BaseModel):
    source_meal_id: str | None = None
    limit: int = Field(default=3, ge=1, le=5)


class AgentCandidateScoresResponse(BaseModel):
    preference_fit: float
    temporal_fit: float
    adherence_likelihood: float
    health_gain: float
    substitution_deviation_penalty: float
    total_score: float


class AgentHealthDeltaResponse(BaseModel):
    calories: float
    sugar_g: float
    sodium_mg: float


class AgentRecommendationCardResponse(BaseModel):
    candidate_id: str
    slot: Literal["breakfast", "lunch", "dinner", "snack"]
    title: str
    venue_type: str
    why_it_fits: list[str] = Field(default_factory=list)
    caution_notes: list[str] = Field(default_factory=list)
    confidence: float
    scores: AgentCandidateScoresResponse
    health_gain_summary: AgentHealthDeltaResponse


class AgentSourceMealResponse(BaseModel):
    meal_id: str
    title: str
    slot: Literal["breakfast", "lunch", "dinner", "snack"]


class AgentSubstitutionAlternativeResponse(BaseModel):
    candidate_id: str
    title: str
    venue_type: str
    health_delta: AgentHealthDeltaResponse
    taste_distance: float
    reasoning: str
    confidence: float


class AgentSubstitutionPlanResponse(BaseModel):
    source_meal: AgentSourceMealResponse
    alternatives: list[AgentSubstitutionAlternativeResponse] = Field(default_factory=list)
    blocked_reason: str | None = None


class RecommendationSubstitutionResponse(AgentSubstitutionPlanResponse):
    pass


class RecommendationAgentProfileStateResponse(BaseModel):
    completeness_state: str
    bmi: float | None = None
    target_calories_per_day: float | None = None
    macro_focus: list[str] = Field(default_factory=list)


class RecommendationAgentTemporalContextResponse(BaseModel):
    current_slot: Literal["breakfast", "lunch", "dinner", "snack"]
    generated_at: datetime
    meal_history_count: int
    interaction_count: int
    recent_repeat_titles: list[str] = Field(default_factory=list)
    slot_history_counts: dict[str, int] = Field(default_factory=dict)


class RecommendationAgentResponse(BaseModel):
    profile_state: RecommendationAgentProfileStateResponse
    temporal_context: RecommendationAgentTemporalContextResponse
    recommendations: dict[str, AgentRecommendationCardResponse]
    substitutions: AgentSubstitutionPlanResponse | None = None
    fallback_mode: bool
    data_sources: dict[str, object] = Field(default_factory=dict)
    constraints_applied: list[str] = Field(default_factory=list)
    workflow: dict[str, object]


class SuggestionListResponse(BaseModel):
    items: list[SuggestionItemResponse]


class SuggestionDetailResponse(BaseModel):
    suggestion: SuggestionItemResponse


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
