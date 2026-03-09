"""Meal, medication, symptom, clinical-card, and metric API contracts."""

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


from .core import CursorPageResponse, HealthProfileResponseItem, HouseholdCareContextResponse

from .workflows import WorkflowResponse

class MealAnalyzeSummaryResponse(BaseModel):
    meal_record_id: str
    meal_name: str
    confidence: float
    identification_method: str
    estimated_calories: float
    portion_size: str
    needs_manual_review: bool
    flags: list[str] = Field(default_factory=list)
    portion_notes: list[str] = Field(default_factory=list)
    captured_at: datetime


class MealAnalyzeResponse(BaseModel):
    summary: MealAnalyzeSummaryResponse
    vision_result: VisionResult
    meal_record: MealRecognitionRecord
    output_envelope: AgentOutputEnvelope | None
    workflow: "WorkflowResponse"


class MealRecordsResponse(BaseModel):
    records: list[MealRecognitionRecord]
    page: CursorPageResponse | None = None


class DailyNutritionTotalsResponse(BaseModel):
    calories: float
    sugar_g: float
    sodium_mg: float
    protein_g: float
    fiber_g: float


class DailyNutritionInsightResponse(BaseModel):
    code: str
    title: str
    summary: str
    actions: list[str] = Field(default_factory=list)


class MealDailySummaryResponse(BaseModel):
    date: str
    meal_count: int
    last_logged_at: datetime | None = None
    consumed: DailyNutritionTotalsResponse
    targets: DailyNutritionTotalsResponse
    remaining: DailyNutritionTotalsResponse
    insights: list[DailyNutritionInsightResponse] = Field(default_factory=list)
    recommendation_hints: list[str] = Field(default_factory=list)


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


class HouseholdCareProfileResponse(BaseModel):
    context: HouseholdCareContextResponse
    profile: HealthProfileResponseItem


class HouseholdCareMealSummaryResponse(BaseModel):
    context: HouseholdCareContextResponse
    summary: MealDailySummaryResponse


class HouseholdCareReminderListResponse(BaseModel):
    context: HouseholdCareContextResponse
    reminders: list[ReminderEvent] = Field(default_factory=list)
    metrics: EngagementMetrics = Field(default_factory=lambda: EngagementMetrics(
        reminders_sent=0,
        meal_confirmed_yes=0,
        meal_confirmed_no=0,
        meal_confirmation_rate=0.0,
    ))


MealAnalyzeResponse.model_rebuild(_types_namespace={"WorkflowResponse": WorkflowResponse})

