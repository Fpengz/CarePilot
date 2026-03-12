"""
Define meal and health-adjacent API contracts.

This module contains request/response schemas for meals, medications,
symptoms, clinical cards, and health metrics endpoints.
"""

from __future__ import annotations

# ruff: noqa: F401
from datetime import date, datetime, timezone
from typing import Literal, TypeAlias

from pydantic import BaseModel, EmailStr, Field, RootModel

from dietary_guardian.features.safety.domain.alerts.models import OutboxState
from dietary_guardian.features.companion.core.health.models import (
    BiomarkerReading,
    ClinicalProfileSnapshot,
)
from dietary_guardian.features.profiles.domain.models import (
    AccountRole,
    MealScheduleWindow,
    MealSlot,
    ProfileMode,
)
from dietary_guardian.features.reminders.domain.models import ReminderEvent
from dietary_guardian.features.recommendations.domain.models import (
    InteractionEventType,
    RecommendationOutput,
)
from dietary_guardian.features.companion.core.health.analytics import EngagementMetrics
from dietary_guardian.core.contracts.agent_envelopes import AgentOutputEnvelope
from dietary_guardian.features.companion.core.health.emotion import (
    EmotionConfidenceBand,
    EmotionLabel,
    EmotionRuntimeHealth,
)
from dietary_guardian.features.meals.domain.models import NutritionRiskProfile, RawObservationBundle, ValidatedMealEvent
from dietary_guardian.features.households.schemas import (  # noqa: F401
    HouseholdCareMealSummaryResponse,
    HouseholdCareProfileResponse,
    HouseholdCareReminderListResponse,
)
from dietary_guardian.features.meals.schemas import (  # noqa: F401
    DailyNutritionInsightResponse,
    DailyNutritionTotalsResponse,
    MealDailySummaryResponse,
)
from dietary_guardian.platform.observability.tooling.domain.models import ToolExecutionResult

from .core import CursorPageResponse, HealthProfileResponseItem, HouseholdCareContextResponse
from .workflows import WorkflowResponse


class MealAnalyzeResponse(BaseModel):
    raw_observation: RawObservationBundle
    validated_event: ValidatedMealEvent
    nutrition_profile: NutritionRiskProfile
    output_envelope: AgentOutputEnvelope | None = None
    workflow: "WorkflowResponse"


class MealRecordsResponse(BaseModel):
    records: list[ValidatedMealEvent]
    page: CursorPageResponse | None = None



class MealWeeklySummaryDayResponse(BaseModel):
    meal_count: int
    calories: float
    sugar_g: float
    sodium_mg: float


class MealWeeklySummaryResponse(BaseModel):
    week_start: str
    week_end: str
    meal_count: int
    totals: DailyNutritionTotalsResponse
    daily_breakdown: dict[str, MealWeeklySummaryDayResponse] = Field(default_factory=dict)
    pattern_flags: list[str] = Field(default_factory=list)


class MedicationRegimenCreateRequest(BaseModel):
    medication_name: str
    dosage_text: str
    timing_type: Literal["pre_meal", "post_meal", "fixed_time"]
    offset_minutes: int = 0
    slot_scope: list[Literal["breakfast", "lunch", "dinner", "snack"]] = Field(default_factory=list)
    fixed_time: str | None = None
    max_daily_doses: int = Field(default=1, ge=1, le=8)
    active: bool = True


class MedicationRegimenPatchRequest(BaseModel):
    medication_name: str | None = None
    dosage_text: str | None = None
    timing_type: Literal["pre_meal", "post_meal", "fixed_time"] | None = None
    offset_minutes: int | None = None
    slot_scope: list[Literal["breakfast", "lunch", "dinner", "snack"]] | None = None
    fixed_time: str | None = None
    max_daily_doses: int | None = Field(default=None, ge=1, le=8)
    active: bool | None = None


class MedicationRegimenResponse(BaseModel):
    id: str
    medication_name: str
    dosage_text: str
    timing_type: Literal["pre_meal", "post_meal", "fixed_time"]
    offset_minutes: int
    slot_scope: list[Literal["breakfast", "lunch", "dinner", "snack"]] = Field(default_factory=list)
    fixed_time: str | None = None
    max_daily_doses: int
    active: bool


class MedicationRegimenEnvelopeResponse(BaseModel):
    regimen: MedicationRegimenResponse


class MedicationRegimenListResponse(BaseModel):
    items: list[MedicationRegimenResponse] = Field(default_factory=list)


class MedicationRegimenDeleteResponse(BaseModel):
    ok: bool = True
    deleted: bool


class MedicationAdherenceEventCreateRequest(BaseModel):
    regimen_id: str
    reminder_id: str | None = None
    status: Literal["taken", "missed", "skipped", "unknown"]
    scheduled_at: datetime
    taken_at: datetime | None = None
    source: Literal["manual", "reminder_confirm", "imported"] = "manual"
    metadata: dict[str, object] = Field(default_factory=dict)


class MedicationAdherenceEventResponse(BaseModel):
    id: str
    regimen_id: str
    reminder_id: str | None = None
    status: Literal["taken", "missed", "skipped", "unknown"]
    scheduled_at: datetime
    taken_at: datetime | None = None
    source: Literal["manual", "reminder_confirm", "imported"]
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class MedicationAdherenceEventEnvelopeResponse(BaseModel):
    event: MedicationAdherenceEventResponse


class MedicationAdherenceTotalsResponse(BaseModel):
    events: int
    taken: int
    missed: int
    skipped: int
    adherence_rate: float


class MedicationAdherenceMetricsResponse(BaseModel):
    totals: MedicationAdherenceTotalsResponse
    events: list[MedicationAdherenceEventResponse] = Field(default_factory=list)


class SymptomCheckInRequest(BaseModel):
    severity: int = Field(ge=1, le=5)
    symptom_codes: list[str] = Field(default_factory=list)
    free_text: str | None = None
    context: dict[str, object] = Field(default_factory=dict)


class SymptomSafetyResponse(BaseModel):
    decision: str
    reasons: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    redactions: list[str] = Field(default_factory=list)


class SymptomCheckInResponse(BaseModel):
    id: str
    recorded_at: datetime
    severity: int
    symptom_codes: list[str] = Field(default_factory=list)
    free_text: str | None = None
    context: dict[str, object] = Field(default_factory=dict)
    safety: SymptomSafetyResponse


class SymptomCheckInEnvelopeResponse(BaseModel):
    item: SymptomCheckInResponse


class SymptomCheckInListResponse(BaseModel):
    items: list[SymptomCheckInResponse] = Field(default_factory=list)


class SymptomCountResponse(BaseModel):
    code: str
    count: int


class SymptomSummaryResponse(BaseModel):
    total_count: int
    average_severity: float
    red_flag_count: int
    top_symptoms: list[SymptomCountResponse] = Field(default_factory=list)
    latest_recorded_at: datetime | None = None


class ClinicalCardGenerateRequest(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    format: Literal["sectioned", "soap"] = "sectioned"


class ClinicalCardTrendResponse(BaseModel):
    metric: str
    delta: float
    percent_change: float | None = None
    slope_per_point: float
    direction: Literal["increase", "decrease", "flat"]
    point_count: int


class ClinicalCardProvenanceResponse(BaseModel):
    meal_record_count: int = 0
    symptom_checkin_count: int = 0
    biomarker_reading_count: int = 0
    adherence_event_count: int = 0


class ClinicalCardResponse(BaseModel):
    id: str
    created_at: datetime
    start_date: str
    end_date: str
    format: Literal["sectioned", "soap"]
    sections: dict[str, str] = Field(default_factory=dict)
    deltas: dict[str, float] = Field(default_factory=dict)
    trends: dict[str, ClinicalCardTrendResponse] = Field(default_factory=dict)
    provenance: ClinicalCardProvenanceResponse


class ClinicalCardEnvelopeResponse(BaseModel):
    card: ClinicalCardResponse


class ClinicalCardListResponse(BaseModel):
    items: list[ClinicalCardResponse] = Field(default_factory=list)


class MetricTrendPointResponse(BaseModel):
    timestamp: datetime
    value: float


class MetricTrendResponse(BaseModel):
    metric: str
    points: list[MetricTrendPointResponse] = Field(default_factory=list)
    delta: float
    percent_change: float | None = None
    slope_per_point: float
    direction: Literal["increase", "decrease", "flat"]


class MetricTrendListResponse(BaseModel):
    items: list[MetricTrendResponse] = Field(default_factory=list)



MealAnalyzeResponse.model_rebuild(_types_namespace={"WorkflowResponse": WorkflowResponse})
