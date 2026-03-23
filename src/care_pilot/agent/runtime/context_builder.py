"""Helper to construct AgentContext with policy + selection metadata."""

from __future__ import annotations

from typing import Any

from care_pilot.agent.core.base import AgentContext
from care_pilot.platform.observability.setup import get_logger

logger = get_logger(__name__)


def build_agent_context(
    *,
    user_id: str | None,
    session_id: str | None,
    request_id: str | None,
    correlation_id: str | None,
    policy: dict[str, Any] | None = None,
    selection: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AgentContext:
    merged: dict[str, Any] = {}
    if metadata:
        merged.update(metadata)
    if policy is not None:
        merged["policy"] = policy
    if selection is not None:
        merged["selection"] = selection
    if policy is not None or selection is not None:
        logger.info(
            "agent_context_built user_id=%s request_id=%s correlation_id=%s policy_keys=%s selection_keys=%s",
            user_id,
            request_id,
            correlation_id,
            list((policy or {}).keys()),
            list((selection or {}).keys()),
        )
    return AgentContext(
        user_id=user_id,
        session_id=session_id,
        request_id=request_id,
        correlation_id=correlation_id,
        metadata=merged,
    )


__all__ = ["build_agent_context"]
