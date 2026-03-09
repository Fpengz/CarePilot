from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["low", "medium", "high"]
EngagementMode = Literal["supportive", "accountability", "follow_up", "escalate"]
UrgencyLevel = Literal["routine", "soon", "prompt"]
InteractionType = Literal["chat", "meal_review", "check_in", "report_follow_up", "adherence_follow_up"]
PolicyStatus = Literal["approved", "adjusted", "escalate"]
DigestPriority = Literal["routine", "watch", "urgent"]
InteractionGoal = Literal["education", "next_step", "swap", "recovery", "monitoring"]


class CaseSnapshot(BaseModel):
    user_id: str
    profile_name: str
    conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    meal_count: int = 0
    latest_meal_name: str | None = None
    meal_risk_streak: int = 0
    reminder_count: int = 0
    reminder_response_rate: float = 0.0
    adherence_events: int = 0
    adherence_rate: float | None = None
    symptom_count: int = 0
    average_symptom_severity: float = 0.0
    biomarker_summary: dict[str, float] = Field(default_factory=dict)
    active_risk_flags: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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
    snapshot: CaseSnapshot
    engagement: EngagementAssessment
    care_plan: CarePlan
    clinician_digest_preview: ClinicianDigest
    impact: ImpactSummary
    evidence: EvidenceBundle
    safety: SafetyDecision
