from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field

from dietary_guardian.models.contracts import AgentOutputEnvelope, AgentHandoff
from dietary_guardian.models.tooling import ToolExecutionResult


class WorkflowName(StrEnum):
    MEAL_ANALYSIS = "meal_analysis"
    ALERT_ONLY = "alert_only"
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

