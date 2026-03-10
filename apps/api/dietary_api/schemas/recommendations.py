"""Recommendation, suggestion, report, and reminder generation API contracts."""

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
from dietary_guardian.models.analytics import EngagementMetrics
from dietary_guardian.models.contracts import AgentOutputEnvelope
from dietary_guardian.models.emotion import (
    EmotionConfidenceBand,
    EmotionLabel,
    EmotionRuntimeHealth,
)
from dietary_guardian.models.meal import VisionResult
from dietary_guardian.models.meal_record import MealRecognitionRecord
from dietary_guardian.models.tooling import ToolExecutionResult

from .core import HealthProfileResponseItem, JsonValue
from .meal_health import SymptomSummaryResponse
from .workflows import WorkflowResponse


class ReportParseRequest(BaseModel):
    source: Literal["pasted_text"] = "pasted_text"
    text: str


class SymptomSummaryWindowResponse(BaseModel):
    from_date: date = Field(serialization_alias="from")
    to_date: date = Field(serialization_alias="to")
    limit: int


class ReportParseResponse(BaseModel):
    readings: list[BiomarkerReading]
    snapshot: ClinicalProfileSnapshot
    symptom_summary: SymptomSummaryResponse
    symptom_window: SymptomSummaryWindowResponse


class RecommendationGenerateResponse(BaseModel):
    recommendation: RecommendationOutput
    workflow: WorkflowResponse


class SuggestionGenerateFromReportRequest(BaseModel):
    source: Literal["pasted_text"] = "pasted_text"
    text: str


class SafetyDecisionResponse(BaseModel):
    decision: Literal["allow", "modify", "refuse", "escalate", "ask_clarification"]
    reasons: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    redactions: list[str] = Field(default_factory=list)


class SuggestionReportParseResponse(BaseModel):
    readings: list[BiomarkerReading]
    snapshot: ClinicalProfileSnapshot


class SuggestionItemResponse(BaseModel):
    suggestion_id: str
    created_at: datetime
    source_user_id: str
    source_display_name: str
    disclaimer: str
    safety: SafetyDecisionResponse
    report_parse: SuggestionReportParseResponse
    recommendation: RecommendationOutput
    workflow: WorkflowResponse


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


class RecommendationInteractionItemResponse(BaseModel):
    interaction_id: str
    user_id: str
    recommendation_id: str
    candidate_id: str
    event_type: InteractionEventType
    slot: MealSlot
    source_meal_id: str | None = None
    selected_meal_id: str | None = None
    created_at: datetime
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class RecommendationPreferenceSnapshotResponse(BaseModel):
    user_id: str
    updated_at: datetime
    interaction_count: int = 0
    accepted_count: int = 0
    dismissed_count: int = 0
    swap_selected_count: int = 0
    cuisine_affinity: dict[str, float] = Field(default_factory=dict)
    ingredient_affinity: dict[str, float] = Field(default_factory=dict)
    health_tag_affinity: dict[str, float] = Field(default_factory=dict)
    slot_affinity: dict[str, float] = Field(default_factory=dict)
    substitution_tolerance: float = 0.6
    adherence_bias: float = 0.0


class RecommendationInteractionResponse(BaseModel):
    ok: bool = True
    interaction: RecommendationInteractionItemResponse
    preference_snapshot: RecommendationPreferenceSnapshotResponse


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
    reminders: list[ReminderEvent]
    metrics: EngagementMetrics


class ReminderListResponse(BaseModel):
    reminders: list[ReminderEvent]
    metrics: EngagementMetrics


class ReminderConfirmRequest(BaseModel):
    confirmed: bool


class ReminderConfirmResponse(BaseModel):
    event: ReminderEvent
    metrics: EngagementMetrics


class MobilityReminderSettingsRequest(BaseModel):
    enabled: bool = False
    interval_minutes: int = Field(default=120, ge=60, le=240)
    active_start_time: str = "08:00"
    active_end_time: str = "20:00"


class MobilityReminderSettingsResponse(BaseModel):
    enabled: bool
    interval_minutes: int
    active_start_time: str
    active_end_time: str


class MobilityReminderSettingsEnvelopeResponse(BaseModel):
    settings: MobilityReminderSettingsResponse
