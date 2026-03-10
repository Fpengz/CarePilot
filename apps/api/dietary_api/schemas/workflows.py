"""Workflow, alert timeline, companion, and governance API contracts."""

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
from dietary_guardian.domain.health.analytics import EngagementMetrics
from dietary_guardian.application.contracts.agent_envelopes import AgentOutputEnvelope
from dietary_guardian.domain.health.emotion import (
    EmotionConfidenceBand,
    EmotionLabel,
    EmotionRuntimeHealth,
)
from dietary_guardian.domain.meals.models import VisionResult
from dietary_guardian.domain.meals.recognition import MealRecognitionRecord
from dietary_guardian.domain.tooling.models import ToolExecutionResult

from .core import JsonValue
from .notifications import AlertTimelineItemResponse, WorkflowTimelineEventPayloadResponse


class WorkflowTimelineEventResponse(BaseModel):
    event_id: str
    event_type: str
    workflow_name: str | None = None
    request_id: str | None = None
    correlation_id: str
    user_id: str | None = None
    payload: WorkflowTimelineEventPayloadResponse = Field(default_factory=lambda: WorkflowTimelineEventPayloadResponse({}))
    created_at: datetime


class WorkflowResponse(BaseModel):
    workflow_name: str
    request_id: str
    correlation_id: str
    replayed: bool
    timeline_events: list[WorkflowTimelineEventResponse] = Field(default_factory=list)


class AlertTriggerResponse(BaseModel):
    tool_result: ToolExecutionResult
    outbox_timeline: list[AlertTimelineItemResponse]
    workflow: WorkflowResponse


class AlertTimelineResponse(BaseModel):
    alert_id: str
    outbox_timeline: list[AlertTimelineItemResponse]


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


class WorkflowRuntimeStepResponse(BaseModel):
    step_id: str
    agent_id: str
    capability: str
    tool_names: list[str] = Field(default_factory=list)


class WorkflowRuntimeContractResponse(BaseModel):
    workflow_name: str
    steps: list[WorkflowRuntimeStepResponse] = Field(default_factory=list)


class AgentContractResponse(BaseModel):
    agent_id: str
    capabilities: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    output_contract: str


class CompanionInteractionRequest(BaseModel):
    interaction_type: Literal["chat", "meal_review", "check_in", "report_follow_up", "adherence_follow_up"]
    message: str = Field(min_length=1)
    emotion_text: str | None = None


class CompanionInteractionInfoResponse(BaseModel):
    interaction_type: Literal["chat", "meal_review", "check_in", "report_follow_up", "adherence_follow_up"]
    message: str
    request_id: str
    correlation_id: str
    emotion_signal: str | None = None


class CompanionSnapshotResponse(BaseModel):
    user_id: str
    profile_name: str
    conditions: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    meal_count: int
    latest_meal_name: str | None = None
    meal_risk_streak: int
    reminder_count: int
    reminder_response_rate: float
    adherence_events: int
    adherence_rate: float | None = None
    symptom_count: int
    average_symptom_severity: float
    biomarker_summary: dict[str, float] = Field(default_factory=dict)
    active_risk_flags: list[str] = Field(default_factory=list)
    generated_at: datetime


class CompanionEngagementResponse(BaseModel):
    risk_level: Literal["low", "medium", "high"]
    recommended_mode: Literal["supportive", "accountability", "follow_up", "escalate"]
    rationale: list[str] = Field(default_factory=list)
    intervention_opportunities: int = 0


class CompanionEvidenceCitationResponse(BaseModel):
    title: str
    summary: str
    source_type: str
    relevance: str
    confidence: float


class CompanionCarePlanResponse(BaseModel):
    interaction_type: Literal["chat", "meal_review", "check_in", "report_follow_up", "adherence_follow_up"]
    headline: str
    summary: str
    reasoning_summary: str
    why_now: str
    recommended_actions: list[str] = Field(default_factory=list)
    clinician_follow_up: bool = False
    urgency: Literal["routine", "soon", "prompt"] = "routine"
    citations: list[CompanionEvidenceCitationResponse] = Field(default_factory=list)
    policy_status: Literal["approved", "adjusted", "escalate"] = "approved"


class ClinicianDigestResponse(BaseModel):
    summary: str
    what_changed: list[str] = Field(default_factory=list)
    why_now: str
    time_window: str
    priority: Literal["routine", "watch", "urgent"]
    recommended_actions: list[str] = Field(default_factory=list)
    interventions_attempted: list[str] = Field(default_factory=list)
    citations: list[CompanionEvidenceCitationResponse] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"]


class ImpactSummaryPayloadResponse(BaseModel):
    baseline_window: str
    comparison_window: str
    tracked_metrics: dict[str, float | int] = Field(default_factory=dict)
    deltas: dict[str, float] = Field(default_factory=dict)
    intervention_opportunities: int = 0
    interventions_measured: list[str] = Field(default_factory=list)
    improvement_signals: list[str] = Field(default_factory=list)


class CompanionTodayResponse(BaseModel):
    snapshot: CompanionSnapshotResponse
    engagement: CompanionEngagementResponse
    care_plan: CompanionCarePlanResponse
    impact: ImpactSummaryPayloadResponse


class CompanionInteractionResponse(BaseModel):
    interaction: CompanionInteractionInfoResponse
    snapshot: CompanionSnapshotResponse
    engagement: CompanionEngagementResponse
    care_plan: CompanionCarePlanResponse
    clinician_digest_preview: ClinicianDigestResponse
    impact: ImpactSummaryPayloadResponse
    workflow: WorkflowResponse


class ClinicianDigestEnvelopeResponse(BaseModel):
    digest: ClinicianDigestResponse


class ImpactSummaryResponse(BaseModel):
    summary: ImpactSummaryPayloadResponse


class WorkflowRuntimeRegistryResponse(BaseModel):
    workflows: list[WorkflowRuntimeContractResponse] = Field(default_factory=list)
    agents: list[AgentContractResponse] = Field(default_factory=list)


class ToolPolicyCreateRequest(BaseModel):
    role: Literal["member", "admin"]
    agent_id: str
    tool_name: str
    effect: Literal["allow", "deny"]
    conditions: dict[str, object] = Field(default_factory=dict)
    priority: int = 0
    enabled: bool = True


class ToolPolicyPatchRequest(BaseModel):
    effect: Literal["allow", "deny"] | None = None
    conditions: dict[str, object] | None = None
    priority: int | None = None
    enabled: bool | None = None


class ToolPolicyItemResponse(BaseModel):
    id: str
    role: Literal["member", "admin"]
    agent_id: str
    tool_name: str
    effect: Literal["allow", "deny"]
    conditions: dict[str, object] = Field(default_factory=dict)
    priority: int
    enabled: bool
    created_at: datetime
    updated_at: datetime


class ToolPolicyListResponse(BaseModel):
    items: list[ToolPolicyItemResponse] = Field(default_factory=list)


class ToolPolicyWriteResponse(BaseModel):
    policy: ToolPolicyItemResponse


class ToolPolicyEvaluationResponse(BaseModel):
    policy_mode: Literal["shadow", "enforce"]
    code_decision: Literal["allow", "deny"]
    db_decision: Literal["allow", "deny"] | None = None
    effective_decision: Literal["allow", "deny"]
    diverged: bool
    matched_policy_id: str | None = None


class WorkflowSnapshotItemResponse(BaseModel):
    id: str
    version: int
    contract_hash: str
    source: Literal["startup_bootstrap", "manual_api"]
    created_by: str | None = None
    created_at: datetime


class WorkflowSnapshotListResponse(BaseModel):
    items: list[WorkflowSnapshotItemResponse] = Field(default_factory=list)


class WorkflowSnapshotWriteResponse(BaseModel):
    snapshot: WorkflowSnapshotItemResponse


class WorkflowSnapshotCompareResponse(BaseModel):
    base_version: int
    target_version: int
    changed: bool
    base_hash: str
    target_hash: str

