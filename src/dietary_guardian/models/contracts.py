from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

SCHEMA_VERSION_V1 = "1.0"


class EvidenceItem(BaseModel):
    source_type: str
    source_id: str | None = None
    confidence: float | None = None
    applicability_scope: str | None = None
    summary: str | None = None


class DomainDecision(BaseModel):
    schema_version: str = SCHEMA_VERSION_V1
    decision_type: str
    summary: str
    confidence: float | None = None
    policy_flags: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PresentationMessage(BaseModel):
    schema_version: str = SCHEMA_VERSION_V1
    channel: str
    title: str
    body: str
    severity: str = "info"
    metadata: dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditRecord(BaseModel):
    schema_version: str = SCHEMA_VERSION_V1
    request_id: str
    correlation_id: str
    user_id: str | None = None
    profile_mode: str | None = None
    source: str
    confidence: float | None = None
    trace_metadata: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentExecutionTrace(BaseModel):
    schema_version: str = SCHEMA_VERSION_V1
    request_id: str
    correlation_id: str
    user_id: str | None = None
    profile_mode: str | None = None
    agent_name: str
    tool_calls: list[str] = Field(default_factory=list)
    trace_metadata: dict[str, str] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None


class AgentInputEnvelope(BaseModel):
    schema_version: str = SCHEMA_VERSION_V1
    request_id: str
    correlation_id: str
    user_id: str | None = None
    profile_mode: str | None = None
    source: str
    modality: str
    payload: dict[str, Any] = Field(default_factory=dict)
    policy_flags: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CaptureEnvelope(BaseModel):
    schema_version: str = SCHEMA_VERSION_V1
    capture_id: str
    request_id: str
    correlation_id: str
    user_id: str | None = None
    source: str
    modality: str
    mime_type: str
    filename: str | None = None
    content_sha256: str
    metadata: dict[str, str] = Field(default_factory=dict)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentOutputEnvelope(BaseModel):
    schema_version: str = SCHEMA_VERSION_V1
    request_id: str
    correlation_id: str
    user_id: str | None = None
    profile_mode: str | None = None
    domain_decision: DomainDecision
    presentation_messages: list[PresentationMessage] = Field(default_factory=list)
    audit_record: AuditRecord
    trace: AgentExecutionTrace
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentHandoff(BaseModel):
    schema_version: str = SCHEMA_VERSION_V1
    from_agent: str
    to_agent: str
    request_id: str
    correlation_id: str
    confidence: float | None = None
    obligations: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
