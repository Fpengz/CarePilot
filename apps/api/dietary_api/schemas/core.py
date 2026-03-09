"""Core API schema primitives plus auth, emotion, profile, and household contracts."""

from __future__ import annotations

# ruff: noqa: F401

from datetime import date, datetime, timezone
from typing import Literal, TypeAlias

from pydantic import BaseModel, Field, EmailStr, RootModel
from dietary_guardian.models.identity import AccountRole, ProfileMode
from dietary_guardian.models.analytics import EngagementMetrics
from dietary_guardian.models.alerting import OutboxState
from dietary_guardian.models.contracts import AgentOutputEnvelope
from dietary_guardian.models.emotion import EmotionConfidenceBand, EmotionLabel, EmotionRuntimeHealth
from dietary_guardian.models.meal import VisionResult
from dietary_guardian.models.meal_record import MealRecognitionRecord
from dietary_guardian.models.medication import ReminderEvent
from dietary_guardian.models.recommendation import RecommendationOutput
from dietary_guardian.models.recommendation_agent import InteractionEventType, MealSlot
from dietary_guardian.models.report import BiomarkerReading, ClinicalProfileSnapshot
from dietary_guardian.models.tooling import ToolExecutionResult
from dietary_guardian.models.user import MealScheduleWindow


JsonScalar: TypeAlias = str | int | float | bool | None
JsonObjectValue: TypeAlias = JsonScalar | list[JsonScalar]
JsonValue: TypeAlias = JsonObjectValue | dict[str, JsonObjectValue]


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


class EmotionTextRequest(BaseModel):
    text: str
    language: str | None = None


class EmotionEvidenceResponse(BaseModel):
    label: EmotionLabel
    score: float = Field(ge=0.0, le=1.0)


class EmotionObservationResponse(BaseModel):
    source_type: Literal["text", "speech", "mixed"]
    emotion: EmotionLabel
    score: float = Field(ge=0.0, le=1.0)
    confidence_band: EmotionConfidenceBand
    model_name: str
    model_version: str
    evidence: list[EmotionEvidenceResponse] = Field(default_factory=list)
    transcription: str | None = None
    created_at: datetime
    request_id: str | None = None
    correlation_id: str | None = None


class EmotionInferenceResponse(BaseModel):
    observation: EmotionObservationResponse


class EmotionHealthResponse(EmotionRuntimeHealth):
    pass


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
    daily_protein_target_g: float
    daily_fiber_target_g: float
    target_calories_per_day: float | None = None
    macro_focus: list[str] = Field(default_factory=list)
    conditions: list[HealthProfileCondition] = Field(default_factory=list)
    medications: list[HealthProfileMedication] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    nutrition_goals: list[str] = Field(default_factory=list)
    preferred_cuisines: list[str] = Field(default_factory=list)
    disliked_ingredients: list[str] = Field(default_factory=list)
    budget_tier: Literal["budget", "moderate", "flexible"] = "moderate"
    meal_schedule: list[MealScheduleWindow] = Field(default_factory=list)
    preferred_notification_channel: str = "in_app"
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
    daily_protein_target_g: float | None = Field(default=None, gt=0)
    daily_fiber_target_g: float | None = Field(default=None, gt=0)
    target_calories_per_day: float | None = Field(default=None, gt=0)
    macro_focus: list[str] | None = None
    conditions: list[HealthProfileCondition] | None = None
    medications: list[HealthProfileMedication] | None = None
    allergies: list[str] | None = None
    nutrition_goals: list[str] | None = None
    preferred_cuisines: list[str] | None = None
    disliked_ingredients: list[str] | None = None
    budget_tier: Literal["budget", "moderate", "flexible"] | None = None
    meal_schedule: list[MealScheduleWindow] | None = None
    preferred_notification_channel: str | None = None


class HealthProfileEnvelopeResponse(BaseModel):
    profile: HealthProfileResponseItem


class GuidedHealthStepResponse(BaseModel):
    id: str
    title: str
    description: str
    fields: list[str] = Field(default_factory=list)


class HealthProfileOnboardingStateResponse(BaseModel):
    current_step: str
    completed_steps: list[str] = Field(default_factory=list)
    is_complete: bool = False
    updated_at: datetime | None = None


class HealthProfileOnboardingPatchRequest(BaseModel):
    step_id: str
    profile: HealthProfileUpdateRequest = Field(default_factory=HealthProfileUpdateRequest)


class HealthProfileOnboardingEnvelopeResponse(BaseModel):
    onboarding: HealthProfileOnboardingStateResponse
    profile: HealthProfileResponseItem
    steps: list[GuidedHealthStepResponse] = Field(default_factory=list)


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


class HouseholdCareContextResponse(BaseModel):
    viewer_user_id: str
    subject_user_id: str
    household_id: str


class HouseholdCareMembersResponse(BaseModel):
    viewer_user_id: str
    household_id: str
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



class CursorPageResponse(BaseModel):
    limit: int
    cursor: str | None = None
    next_cursor: str | None = None
    has_more: bool
    returned: int


