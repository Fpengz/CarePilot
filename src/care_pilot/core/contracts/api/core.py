"""
Define core API schema primitives and shared contracts.

This module collects the base request/response models used across auth,
emotion, profile, and household endpoints.
"""

from __future__ import annotations

# ruff: noqa: F401
from datetime import UTC, date, datetime, timezone
from typing import Literal, TypeAlias

from pydantic import BaseModel, EmailStr, Field, RootModel

from care_pilot.agent.emotion.schemas import (
    EmotionContextFeatures,
    EmotionFusionOutput,
    EmotionLabel,
    EmotionProductState,
    EmotionRuntimeHealth,
    FusionTrace,
    SpeechEmotionBranchResult,
    TextEmotionBranchResult,
)
from care_pilot.core.contracts.agent_envelopes import AgentOutputEnvelope
from care_pilot.features.companion.core.health.analytics import EngagementMetrics
from care_pilot.features.companion.core.health.models import (
    BiomarkerReading,
    ClinicalProfileSnapshot,
)
from care_pilot.features.households.schemas import (  # noqa: F401
    HouseholdActiveUpdateRequest,
    HouseholdActiveUpdateResponse,
    HouseholdBundleResponse,
    HouseholdCareContextResponse,
    HouseholdCareMealSummaryResponse,
    HouseholdCareMembersResponse,
    HouseholdCareProfileResponse,
    HouseholdCareReminderListResponse,
    HouseholdCreateRequest,
    HouseholdInviteCreateResponse,
    HouseholdInviteResponseItem,
    HouseholdJoinRequest,
    HouseholdLeaveResponse,
    HouseholdMemberItem,
    HouseholdMemberRemoveResponse,
    HouseholdMembersResponse,
    HouseholdResponse,
    HouseholdUpdateRequest,
)
from care_pilot.features.meals.domain.models import VisionResult
from care_pilot.features.meals.domain.recognition import MealRecognitionRecord
from care_pilot.features.profiles.domain.models import (
    AccountRole,
    MealScheduleWindow,
    MealSlot,
    ProfileMode,
)
from care_pilot.features.profiles.schemas import (  # noqa: F401
    HealthProfileCompletenessResponse,
    HealthProfileCondition,
    HealthProfileMedication,
    HealthProfileResponseItem,
)
from care_pilot.features.recommendations.domain.models import (
    InteractionEventType,
    RecommendationOutput,
)
from care_pilot.features.reminders.domain.models import ReminderEvent
from care_pilot.features.safety.domain.alerts.models import OutboxState
from care_pilot.platform.observability.tooling.domain.models import ToolExecutionResult

type JsonScalar = str | int | float | bool | None
type JsonObjectValue = JsonScalar | list[JsonScalar]
type JsonValue = JsonObjectValue | dict[str, JsonObjectValue]


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
    issued_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


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
    final_emotion: EmotionLabel
    product_state: EmotionProductState
    confidence: float
    text_branch: TextEmotionBranchResult | None = None
    speech_branch: SpeechEmotionBranchResult | None = None
    context_features: EmotionContextFeatures
    fusion_method: str
    model_metadata: dict[str, str] = Field(default_factory=dict)
    trace: FusionTrace
    created_at: datetime
    request_id: str | None = None
    correlation_id: str | None = None


class EmotionInferenceResponse(BaseModel):
    observation: EmotionObservationResponse


class EmotionHealthResponse(EmotionRuntimeHealth):
    pass


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


class CursorPageResponse(BaseModel):
    limit: int
    cursor: str | None = None
    next_cursor: str | None = None
    has_more: bool
    returned: int
