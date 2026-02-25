from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ToolErrorClass(StrEnum):
    VALIDATION = "validation"
    POLICY_BLOCKED = "policy_blocked"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    RETRYABLE = "retryable"
    INTERNAL = "internal"
    NOT_FOUND = "not_found"


class ToolSideEffect(StrEnum):
    READ = "read"
    MUTATE = "mutate"
    EXTERNAL = "external"


class ToolSensitivity(StrEnum):
    LOW = "low"
    PHI = "phi"
    MEDICATION = "medication"
    NOTIFICATION = "notification"


class ToolPolicyContext(BaseModel):
    account_role: str
    scopes: list[str] = Field(default_factory=list)
    environment: str = "dev"
    user_id: str | None = None
    correlation_id: str | None = None


class ToolSpec(BaseModel):
    name: str
    purpose: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    required_scopes: list[str] = Field(default_factory=list)
    allowed_environments: list[str] = Field(default_factory=lambda: ["dev", "test", "prod"])
    side_effect: ToolSideEffect
    sensitivity: ToolSensitivity
    timeout_seconds: int = 30
    retryable: bool = False
    idempotent: bool = True


class ToolExecutionError(BaseModel):
    classification: ToolErrorClass
    message: str
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionResult(BaseModel):
    tool_name: str
    success: bool
    output: BaseModel | None = None
    error: ToolExecutionError | None = None
    latency_ms: float = 0.0
    trace_metadata: dict[str, str] = Field(default_factory=dict)
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
