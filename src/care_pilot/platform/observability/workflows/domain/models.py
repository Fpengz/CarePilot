"""Workflow execution + trace domain models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from care_pilot.core.contracts.agent_envelopes import (
    AgentHandoff,
    AgentOutputEnvelope,
)
from care_pilot.platform.observability.tooling.domain.models import (
    ToolExecutionResult,
)
from care_pilot.platform.observability.tooling.domain.policy_models import (
    ToolPolicyEffect,
    ToolRolePolicyRecord,
)


class WorkflowName(StrEnum):
    MEAL_ANALYSIS = "meal_analysis"
    ALERT_ONLY = "alert_only"
    REPORT_PARSE = "report_parse"
    PRESCRIPTION_INGEST = "prescription_ingest"
    REPLAY = "replay"


class WorkflowTimelineEvent(BaseModel):
    event_id: str
    event_type: str
    workflow_name: str | None = None
    request_id: str | None = None
    correlation_id: str
    user_id: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkflowExecutionResult(BaseModel):
    workflow_name: WorkflowName
    request_id: str
    correlation_id: str
    user_id: str | None = None
    output_envelope: AgentOutputEnvelope | None = None
    handoffs: list[AgentHandoff] = Field(default_factory=list)
    tool_results: list[ToolExecutionResult] = Field(default_factory=list)
    timeline_events: list[WorkflowTimelineEvent] = Field(default_factory=list)
    replayed: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentContract(BaseModel):
    agent_id: str
    capabilities: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    output_contract: str


class WorkflowRuntimeStep(BaseModel):
    step_id: str
    agent_id: str
    capability: str
    tool_names: list[str] = Field(default_factory=list)


class WorkflowRuntimeContract(BaseModel):
    workflow_name: WorkflowName
    steps: list[WorkflowRuntimeStep] = Field(default_factory=list)


__all__ = [
    "ToolPolicyEffect",
    "ToolRolePolicyRecord",
    "AgentContract",
    "WorkflowRuntimeContract",
    "WorkflowRuntimeStep",
    "WorkflowExecutionResult",
    "WorkflowName",
    "WorkflowTimelineEvent",
]
