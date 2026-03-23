"""
BaseAgent-backed helpers for LangGraph nodes.

These wrappers keep agent execution standardized while preserving
existing AgentRequest/AgentResponse contracts.
"""

from __future__ import annotations

from care_pilot.agent.adapters.shadow_agents import (
    AdherenceAgentAdapter,
    CarePlanAgentAdapter,
    MealAgentAdapter,
    MedicationAgentAdapter,
    TrendAgentAdapter,
)
from care_pilot.agent.core.base import AgentContext, AgentResult
from care_pilot.agent.core.contracts import AgentRequest, AgentResponse


async def run_meal_agent_via_adapter(
    *, request: AgentRequest, context: AgentContext
) -> AgentResult[AgentResponse]:
    adapter = MealAgentAdapter()
    return await adapter.run(request, context)


async def run_medication_agent_via_adapter(
    *, request: AgentRequest, context: AgentContext
) -> AgentResult[AgentResponse]:
    adapter = MedicationAgentAdapter()
    return await adapter.run(request, context)


async def run_trend_agent_via_adapter(
    *, request: AgentRequest, context: AgentContext
) -> AgentResult[AgentResponse]:
    adapter = TrendAgentAdapter()
    return await adapter.run(request, context)


async def run_adherence_agent_via_adapter(
    *, request: AgentRequest, context: AgentContext
) -> AgentResult[AgentResponse]:
    adapter = AdherenceAgentAdapter()
    return await adapter.run(request, context)


async def run_care_plan_agent_via_adapter(
    *, request: AgentRequest, context: AgentContext
) -> AgentResult[AgentResponse]:
    adapter = CarePlanAgentAdapter()
    return await adapter.run(request, context)


__all__ = [
    "run_care_plan_agent_via_adapter",
    "run_adherence_agent_via_adapter",
    "run_meal_agent_via_adapter",
    "run_medication_agent_via_adapter",
    "run_trend_agent_via_adapter",
]
