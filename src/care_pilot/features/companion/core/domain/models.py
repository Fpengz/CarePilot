"""
Define companion core domain models.

This module contains core data models used by the companion care loop.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from care_pilot.features.companion.core.health.models import BloodPressureSummary

RiskLevel = Literal["low", "medium", "high"]
EngagementMode = Literal["supportive", "accountability", "follow_up", "escalate"]
UrgencyLevel = Literal["routine", "soon", "prompt"]
InteractionType = Literal[
    "chat", "meal_review", "check_in", "report_follow_up", "adherence_follow_up"
]
PolicyStatus = Literal["approved", "adjusted", "escalate"]
DigestPriority = Literal["routine", "watch", "urgent"]
InteractionGoal = Literal["education", "next_step", "swap", "recovery", "monitoring"]


class PatientCaseSnapshot(BaseModel):
    """A blackboard-style shared state containing all relevant context for a patient."""

    user_id: str
    profile_name: str

    # Static/Semi-static Context
    demographics: dict[str, Any] = Field(default_factory=dict)
    conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    clinician_instructions: list[str] = Field(default_factory=list)

    # Activity/History Context
    meal_count: int = 0
    latest_meal_name: str | None = None
    meal_risk_streak: int = 0
    reminder_count: int = 0
    reminder_response_rate: float = 0.0
    adherence_events: int = 0
    adherence_rate: float | None = None
    symptom_count: int = 0
    average_symptom_severity: float = 0.0
    recent_meals: list[dict[str, Any]] = Field(default_factory=list)
    recent_symptoms: list[dict[str, Any]] = Field(default_factory=list)
    recent_emotion_markers: list[dict[str, Any]] = Field(default_factory=list)

    # Longitudinal Signals
    biomarker_summary: dict[str, float] = Field(default_factory=dict)
    blood_pressure_summary: BloodPressureSummary | None = None
    active_risk_flags: list[str] = Field(default_factory=list)
    trends: dict[str, Any] = Field(default_factory=dict)

    # Interaction/Orchestration Context
    current_conversation_turn: int = 0
    pending_tasks: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    last_interaction_at: datetime | None = None

    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


CaseSnapshot = PatientCaseSnapshot


class PersonalizationContext(BaseModel):
    focus_areas: list[str] = Field(default_factory=list)
    barrier_hints: list[str] = Field(default_factory=list)
    preferred_tone: str = "practical"
    cultural_context: str = "Singapore hawker routines"
    emotion_signal: str | None = None
    interaction_goal: InteractionGoal = "monitoring"
    recommended_explanation_style: str = "concise"
    candidate_intervention_modes: list[str] = Field(default_factory=list)


class EngagementAssessment(BaseModel):
    risk_level: RiskLevel
    recommended_mode: EngagementMode
    rationale: list[str] = Field(default_factory=list)
    intervention_opportunities: int = 0


class EvidenceCitation(BaseModel):
    title: str
    summary: str
    source_type: str = "curated_guidance"
    relevance: str
    confidence: float = 0.7
    url: str | None = None


class EvidenceBundle(BaseModel):
    query: str
    guidance_summary: str | None = None
    citations: list[EvidenceCitation] = Field(default_factory=list)


class SafetyDecision(BaseModel):
    policy_status: PolicyStatus = "approved"
    clinician_follow_up: bool = False
    reasons: list[str] = Field(default_factory=list)


class CarePlan(BaseModel):
    interaction_type: InteractionType
    headline: str
    summary: str
    reasoning_summary: str
    why_now: str
    recommended_actions: list[str] = Field(default_factory=list)
    clinician_follow_up: bool = False
    urgency: UrgencyLevel = "routine"
    citations: list[EvidenceCitation] = Field(default_factory=list)
    policy_status: PolicyStatus = "approved"


class ClinicianDigest(BaseModel):
    summary: str
    what_changed: list[str] = Field(default_factory=list)
    why_now: str
    time_window: str = "Last 7 days"
    priority: DigestPriority = "routine"
    recommended_actions: list[str] = Field(default_factory=list)
    interventions_attempted: list[str] = Field(default_factory=list)
    citations: list[EvidenceCitation] = Field(default_factory=list)
    risk_level: RiskLevel = "low"


class ImpactSummary(BaseModel):
    baseline_window: str
    comparison_window: str
    tracked_metrics: dict[str, float | int] = Field(default_factory=dict)
    deltas: dict[str, float] = Field(default_factory=dict)
    intervention_opportunities: int = 0
    interventions_measured: list[str] = Field(default_factory=list)
    improvement_signals: list[str] = Field(default_factory=list)


class CompanionInteraction(BaseModel):
    interaction_type: InteractionType
    message: str
    request_id: str
    correlation_id: str
    emotion_signal: str | None = None


class CompanionInteractionResult(BaseModel):
    interaction: CompanionInteraction
    snapshot: PatientCaseSnapshot
    engagement: EngagementAssessment
    care_plan: CarePlan
    clinician_digest_preview: ClinicianDigest
    impact: ImpactSummary
    evidence: EvidenceBundle
    safety: SafetyDecision
