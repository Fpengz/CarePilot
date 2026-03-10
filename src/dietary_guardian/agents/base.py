"""Shared runtime contract for all canonical companion agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


@dataclass(slots=True)
class AgentContext:
    """Request-scoped metadata passed to agent runs."""

    user_id: str | None = None
    session_id: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentResult(Generic[OutputT]):
    """Standardized result envelope returned by canonical agents."""

    success: bool
    agent_name: str
    output: OutputT | None = None
    confidence: float | None = None
    rationale: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    raw: dict[str, Any] | None = None


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """Abstract base class for agentic runtime units.

    Subclasses must declare:
    - ``name``: str — agent identifier
    - ``input_schema``: type[InputT] | tuple[type[BaseModel], ...] — Pydantic
      model (or tuple of models) describing accepted inputs.  Agents that
      accept a union of input types must store a tuple so that callers can
      perform ``isinstance(payload, agent.input_schema)`` correctly.
    - ``output_schema``: type[OutputT] — Pydantic model for outputs
    """

    name: str
    input_schema: type[BaseModel] | tuple[type[BaseModel], ...]
    output_schema: type[OutputT]

    @abstractmethod
    async def run(self, input_data: InputT, context: AgentContext) -> AgentResult[OutputT]:
        """Execute the agent against typed input and request context."""
