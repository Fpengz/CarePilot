"""
Define meal and health-adjacent API contracts.

This module contains request/response schemas for meals, medications,
symptoms, clinical cards, and health metrics endpoints.
"""

from __future__ import annotations

# ruff: noqa: F401
from datetime import date, datetime
from typing import Literal, TypeAlias

from pydantic import BaseModel, EmailStr, Field, RootModel

from care_pilot.agent.emotion.schemas import (
    EmotionConfidenceBand,
    EmotionLabel,
    EmotionRuntimeHealth,
)
from care_pilot.config.app import get_settings
from care_pilot.core.contracts.agent_envelopes import AgentOutputEnvelope
from care_pilot.core.contracts.api.core import (
    CursorPageResponse,
    HealthProfileResponseItem,
    HouseholdCareContextResponse,
)
from care_pilot.core.contracts.api.notifications import ScheduledReminderNotificationItemResponse
from care_pilot.core.contracts.api.workflows import WorkflowResponse
from care_pilot.features.companion.core.health.analytics import EngagementMetrics
from care_pilot.features.companion.core.health.models import (
    BiomarkerReading,
    ClinicalProfileSnapshot,
)
from care_pilot.features.households.schemas import (  # noqa: F401
    HouseholdCareMealSummaryResponse,
    HouseholdCareProfileResponse,
    HouseholdCareReminderListResponse,
)
from care_pilot.features.meals.domain.models import (
    CandidateMealEvent,
    NutritionRiskProfile,
    RawObservationBundle,
    ValidatedMealEvent,
)
from care_pilot.features.meals.schemas import (  # noqa: F401
    DailyNutritionInsightResponse,
    DailyNutritionTotalsResponse,
    MealDailySummaryResponse,
)
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


class MealAnalyzeResponse(BaseModel):
    raw_observation: RawObservationBundle
    candidate_event: CandidateMealEvent
    candidate_id: str
    confirmation_required: bool = False
    validated_event: ValidatedMealEvent | None = None
    nutrition_profile: NutritionRiskProfile
    output_envelope: AgentOutputEnvelope | None = None
    workflow: WorkflowResponse


class MealConfirmRequest(BaseModel):
    candidate_id: str
    action: Literal["confirm", "skip"]


class MealConfirmResponse(BaseModel):
    status: Literal["confirmed", "skipped"]
    candidate_id: str
    meal_name: str | None = None


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
    canonical_name: str | None = None
    frequency_type: Literal["times_per_day", "fixed_slots", "fixed_time"] = "fixed_time"
    frequency_times_per_day: int = Field(default=1, ge=1, le=8)
    time_rules: list[dict[str, object]] = Field(default_factory=list)
    offset_minutes: int = 0
    slot_scope: list[Literal["breakfast", "lunch", "dinner", "snack"]] = Field(default_factory=list)
    fixed_time: str | None = None
    max_daily_doses: int = Field(default=1, ge=1, le=8)
    instructions_text: str | None = None
    source_type: Literal["manual", "plain_text", "upload"] = "manual"
    source_filename: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    timezone: str = Field(default_factory=lambda: get_settings().app.timezone)
    parse_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    active: bool = True


class MedicationRegimenPatchRequest(BaseModel):
    medication_name: str | None = None
    canonical_name: str | None = None
    dosage_text: str | None = None
    timing_type: Literal["pre_meal", "post_meal", "fixed_time"] | None = None
    frequency_type: Literal["times_per_day", "fixed_slots", "fixed_time"] | None = None
    frequency_times_per_day: int | None = Field(default=None, ge=1, le=8)
    time_rules: list[dict[str, object]] | None = None
    offset_minutes: int | None = None
    slot_scope: list[Literal["breakfast", "lunch", "dinner", "snack"]] | None = None
    fixed_time: str | None = None
    max_daily_doses: int | None = Field(default=None, ge=1, le=8)
    instructions_text: str | None = None
    source_type: Literal["manual", "plain_text", "upload"] | None = None
    source_filename: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    timezone: str | None = None
    parse_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    active: bool | None = None


class MedicationRegimenResponse(BaseModel):
    id: str
    medication_name: str
    canonical_name: str | None = None
    dosage_text: str
    timing_type: Literal["pre_meal", "post_meal", "fixed_time"]
    frequency_type: Literal["times_per_day", "fixed_slots", "fixed_time"] = "fixed_time"
    frequency_times_per_day: int = 1
    time_rules: list[dict[str, object]] = Field(default_factory=list)
    offset_minutes: int
    slot_scope: list[Literal["breakfast", "lunch", "dinner", "snack"]] = Field(default_factory=list)
    fixed_time: str | None = None
    max_daily_doses: int
    instructions_text: str | None = None
    source_type: Literal["manual", "plain_text", "upload"] = "manual"
    source_filename: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    timezone: str = Field(default_factory=lambda: get_settings().app.timezone)
    parse_confidence: float | None = None
    active: bool = True


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


class MedicationIntakeTextRequest(BaseModel):
    instructions_text: str = Field(min_length=1)
    allow_ambiguous: bool = False


class MedicationIntakeConfirmRequest(BaseModel):
    draft_id: str = Field(min_length=1)


class MedicationDraftInstructionUpdateRequest(BaseModel):
    medication_name_raw: str
    medication_name_canonical: str | None = None
    dosage_text: str
    timing_type: Literal["pre_meal", "post_meal", "fixed_time"]
    frequency_type: Literal["times_per_day", "fixed_slots", "fixed_time"] = "fixed_time"
    frequency_times_per_day: int = Field(default=1, ge=1, le=8)
    offset_minutes: int = 0
    slot_scope: list[Literal["breakfast", "lunch", "dinner", "snack"]] = Field(default_factory=list)
    fixed_time: str | None = None
    time_rules: list[dict[str, object]] = Field(default_factory=list)
    duration_days: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    ambiguities: list[str] = Field(default_factory=list)


class MedicationDraftDeleteResponse(BaseModel):
    ok: bool = True


class MedicationIntakeSourceResponse(BaseModel):
    source_type: Literal["plain_text", "upload"]
    extracted_text: str
    filename: str | None = None
    mime_type: str | None = None
    source_hash: str


class NormalizedMedicationInstructionResponse(BaseModel):
    medication_name_raw: str
    medication_name_canonical: str | None = None
    dosage_text: str
    timing_type: Literal["pre_meal", "post_meal", "fixed_time"]
    frequency_type: Literal["times_per_day", "fixed_slots", "fixed_time"] = "fixed_time"
    frequency_times_per_day: int = 1
    offset_minutes: int = 0
    slot_scope: list[Literal["breakfast", "lunch", "dinner", "snack"]] = Field(default_factory=list)
    fixed_time: str | None = None
    time_rules: list[dict[str, object]] = Field(default_factory=list)
    duration_days: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    confidence: float = 0.0
    ambiguities: list[str] = Field(default_factory=list)


class MedicationIntakeResponse(BaseModel):
    draft_id: str
    source: MedicationIntakeSourceResponse
    normalized_instructions: list[NormalizedMedicationInstructionResponse] = Field(
        default_factory=list
    )
    regimens: list[MedicationRegimenResponse] = Field(default_factory=list)
    reminders: list[ReminderEvent] = Field(default_factory=list)
    scheduled_notifications: list[ScheduledReminderNotificationItemResponse] = Field(
        default_factory=list
    )


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
    bp_reading_count: int = 0


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


type DashboardBucket = Literal["hour", "day", "week"]


class DashboardRangeResponse(BaseModel):
    key: str
    label: str
    from_date: date = Field(alias="from")
    to: date
    bucket: DashboardBucket
    days: int


class DashboardSummaryMetricResponse(BaseModel):
    label: str
    value: float
    unit: str = ""
    delta: float = 0.0
    direction: Literal["up", "down", "flat"] = "flat"
    status: str | None = None
    detail: str | None = None


class DashboardAlertResponse(BaseModel):
    id: str
    severity: Literal["info", "warning", "critical"]
    title: str
    detail: str
    href: str | None = None


class DashboardSeriesPointResponse(BaseModel):
    bucket_start: datetime
    bucket_end: datetime
    label: str
    value: float
    target: float | None = None


class DashboardMacroPointResponse(BaseModel):
    bucket_start: datetime
    bucket_end: datetime
    label: str
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    calories: float = 0.0


class DashboardMealTimingBinResponse(BaseModel):
    hour: int
    label: str
    count: int


class DashboardBloodPressurePointResponse(BaseModel):
    bucket_start: datetime
    bucket_end: datetime
    label: str
    systolic: float
    diastolic: float


class DashboardBloodPressureChartResponse(BaseModel):
    title: str
    bucket: DashboardBucket
    points: list[DashboardBloodPressurePointResponse] = Field(default_factory=list)


class DashboardMetricChartResponse(BaseModel):
    title: str
    bucket: DashboardBucket
    points: list[DashboardSeriesPointResponse] = Field(default_factory=list)


class DashboardMacroChartResponse(BaseModel):
    title: str
    bucket: DashboardBucket
    points: list[DashboardMacroPointResponse] = Field(default_factory=list)


class DashboardMealTimingChartResponse(BaseModel):
    title: str
    bins: list[DashboardMealTimingBinResponse] = Field(default_factory=list)


class DashboardChartsResponse(BaseModel):
    calories: DashboardMetricChartResponse
    macros: DashboardMacroChartResponse
    glycemic_risk: DashboardMetricChartResponse
    adherence: DashboardMetricChartResponse
    meal_timing: DashboardMealTimingChartResponse
    blood_pressure: DashboardBloodPressureChartResponse


class DashboardInsightsResponse(BaseModel):
    recommendations: list[str] = Field(default_factory=list)
    key_drivers: list[str] = Field(default_factory=list)


class DashboardLinksResponse(BaseModel):
    meals: str = "/meals"
    medications: str = "/medications"
    reminders: str = "/reminders"
    metrics: str = "/metrics"


class DashboardSummaryResponse(BaseModel):
    nutrition_goal_score: DashboardSummaryMetricResponse
    adherence_score: DashboardSummaryMetricResponse
    glycemic_risk: DashboardSummaryMetricResponse
    stability_index: DashboardSummaryMetricResponse


class DashboardOverviewResponse(BaseModel):
    range: DashboardRangeResponse
    comparison_range: DashboardRangeResponse
    summary: DashboardSummaryResponse
    alerts: list[DashboardAlertResponse] = Field(default_factory=list)
    charts: DashboardChartsResponse
    insights: DashboardInsightsResponse
    links: DashboardLinksResponse = Field(default_factory=DashboardLinksResponse)


MealAnalyzeResponse.model_rebuild(_types_namespace={"WorkflowResponse": WorkflowResponse})
