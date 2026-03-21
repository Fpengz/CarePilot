"""
Define shared contracts for multi-agent coordination.

This module provides the base request and response envelopes used by all
specialized agents in the companion ecosystem.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Canonical request envelope for specialized agents."""

    user_id: str
    session_id: str
    goal: str
    correlation_id: str | None = None
    context: dict[str, Any] = Field(
        default_factory=dict, description="Case snapshot or relevant feature context."
    )
    memory: dict[str, Any] | None = Field(
        None, description="Short-term or long-term agent memory."
    )
    inputs: dict[str, Any] = Field(
        default_factory=dict, description="Unstructured or typed task-specific inputs."
    )
    constraints: dict[str, Any] | None = Field(
        None, description="Safety, policy, or UI-driven constraints."
    )


class AgentAction(BaseModel):
    """A proposed side-effect or deterministic service call."""

    action_name: str
    params: dict[str, Any] = Field(default_factory=dict)
    rationale: str | None = None


class AgentRecommendation(BaseModel):
    """A suggested next-step or advice for the user."""

    title: str
    summary: str
    priority: Literal["low", "medium", "high"] = "medium"
    category: str | None = None


class AgentResponse(BaseModel):
    """Canonical response envelope for specialized agents."""

    agent_name: str
    status: Literal["success", "needs_handoff", "blocked", "error"] = "success"
    summary: str = Field(description="Human-readable summary of what the agent did/thought.")
    structured_output: dict[str, Any] = Field(
        default_factory=dict, description="The primary result of the agent task."
    )
    recommendations: list[AgentRecommendation] = Field(default_factory=list)
    actions: list[AgentAction] = Field(default_factory=list)
    followups: list[str] = Field(
        default_factory=list, description="Clarifying questions or suggested follow-ups."
    )
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    evidence: list[dict[str, Any]] = Field(
        default_factory=list, description="Supporting data, citations, or rationale."
    )
    handoff_to: str | None = Field(None, description="Name of the agent that should handle next.")
    reasoning_trace: list[str] = Field(
        default_factory=list, description="Internal logic steps for observability."
    )
