"""Domain model definitions for the workflows subdomain: workflow contracts, agent definitions, tool policies, and timeline events."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from dietary_guardian.domain.identity.models import AccountRole
from dietary_guardian.models.contracts import AgentHandoff, AgentOutputEnvelope
from dietary_guardian.models.tooling import ToolExecutionResult

ToolPolicyEffect = Literal["allow", "deny"]


class ToolRolePolicyRecord(BaseModel):
    id: str
    role: AccountRole
    agent_id: str
    tool_name: str
    effect: ToolPolicyEffect
    conditions: dict[str, object] = Field(default_factory=dict)
    priority: int = 0
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkflowName(StrEnum):
    MEAL_ANALYSIS = "meal_analysis"
    ALERT_ONLY = "alert_only"
    REPORT_PARSE = "report_parse"
    REPLAY = "replay"


class WorkflowTimelineEvent(BaseModel):
    event_id: str
    event_type: str
    workflow_name: str | None = None
    request_id: str | None = None
    correlation_id: str
    user_id: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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


WorkflowContractSnapshotSource = Literal["startup_bootstrap", "manual_api"]


class WorkflowContractSnapshotRecord(BaseModel):
    id: str
    version: int
    contract_hash: str
    source: WorkflowContractSnapshotSource
    workflows: list[WorkflowRuntimeContract] = Field(default_factory=list)
    agents: list[AgentContract] = Field(default_factory=list)
    created_by: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
