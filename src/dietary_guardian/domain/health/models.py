"""Domain model definitions for the health subdomain: profiles, symptoms, biomarkers, and medication tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from dietary_guardian.domain.identity.models import MealScheduleWindow, MedicalCondition, Medication


class HealthProfileOnboardingStepDefinition(BaseModel):
    id: str
    title: str
    description: str
    fields: list[str] = Field(default_factory=list)


class HealthProfileOnboardingState(BaseModel):
    user_id: str
    current_step: str = "basic_identity"
    completed_steps: list[str] = Field(default_factory=list)
    is_complete: bool = False
    updated_at: str | None = None


class MetricPoint(BaseModel):
    timestamp: datetime
    value: float


class MetricTrend(BaseModel):
    metric: str
    points: list[MetricPoint] = Field(default_factory=list)
    delta: float = 0.0
    percent_change: float | None = None
    slope_per_point: float = 0.0
    direction: Literal["increase", "decrease", "flat"] = "flat"


class ReportInput(BaseModel):
    source: Literal["pdf", "pasted_text"]
    content_bytes: bytes | None = None
    text: str | None = None
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BiomarkerReading(BaseModel):
    name: str
    value: float
    unit: str | None = None
    reference_range: str | None = None
    measured_at: datetime | None = None
    source_doc_id: str | None = None


class ClinicalProfileSnapshot(BaseModel):
    biomarkers: dict[str, float] = Field(default_factory=dict)
    risk_flags: list[str] = Field(default_factory=list)


class SymptomSafety(BaseModel):
    decision: str = "allow"
    reasons: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
    redactions: list[str] = Field(default_factory=list)


class SymptomCheckIn(BaseModel):
    id: str
    user_id: str
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    severity: int = Field(ge=1, le=5)
    symptom_codes: list[str] = Field(default_factory=list)
    free_text: str | None = None
    context: dict[str, object] = Field(default_factory=dict)
    safety: SymptomSafety = Field(default_factory=SymptomSafety)


class SymptomCount(BaseModel):
    code: str
    count: int


class SymptomSummary(BaseModel):
    total_count: int = 0
    average_severity: float = 0.0
    red_flag_count: int = 0
    top_symptoms: list[SymptomCount] = Field(default_factory=list)
    latest_recorded_at: datetime | None = None


AdherenceStatus = Literal["taken", "missed", "skipped", "unknown"]
AdherenceSource = Literal["manual", "reminder_confirm", "imported"]


class MedicationAdherenceEvent(BaseModel):
    id: str
    user_id: str
    regimen_id: str
    reminder_id: str | None = None
    status: AdherenceStatus
    scheduled_at: datetime
    taken_at: datetime | None = None
    source: AdherenceSource = "manual"
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MedicationAdherenceMetrics(BaseModel):
    events: int = 0
    taken: int = 0
    missed: int = 0
    skipped: int = 0
    adherence_rate: float = 0.0


BudgetTier = Literal["budget", "moderate", "flexible"]
CompletenessState = Literal["needs_profile", "partial", "ready"]


class ProfileCompleteness(BaseModel):
    state: CompletenessState
    missing_fields: list[str] = Field(default_factory=list)


class HealthProfileRecord(BaseModel):
    user_id: str
    age: int | None = None
    locale: str = "en-SG"
    height_cm: float | None = None
    weight_kg: float | None = None
    daily_sodium_limit_mg: float = 2000.0
    daily_sugar_limit_g: float = 30.0
    daily_protein_target_g: float = 60.0
    daily_fiber_target_g: float = 25.0
    target_calories_per_day: float | None = None
    macro_focus: list[str] = Field(default_factory=list)
    conditions: list[MedicalCondition] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    nutrition_goals: list[str] = Field(default_factory=list)
    preferred_cuisines: list[str] = Field(default_factory=list)
    disliked_ingredients: list[str] = Field(default_factory=list)
    budget_tier: BudgetTier = "moderate"
    meal_schedule: list[MealScheduleWindow] = Field(
        default_factory=lambda: [
            MealScheduleWindow(slot="breakfast", start_time="07:00", end_time="09:00"),
            MealScheduleWindow(slot="lunch", start_time="12:00", end_time="14:00"),
            MealScheduleWindow(slot="dinner", start_time="18:00", end_time="20:00"),
        ]
    )
    preferred_notification_channel: str = "in_app"
    updated_at: str | None = None
