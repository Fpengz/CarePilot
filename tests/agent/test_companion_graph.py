"""Tests for the LangGraph companion orchestration."""

from __future__ import annotations

import pytest
from langchain_core.messages import HumanMessage

from care_pilot.agent.core.contracts import AgentResponse
from care_pilot.features.companion.chat.workflows.companion_graph import (
    CompanionState,
    build_companion_graph,
)
from care_pilot.features.companion.core.domain import PatientCaseSnapshot


@pytest.mark.asyncio
async def test_companion_graph_supervisor_routes_to_end(monkeypatch) -> None:
    # Setup minimal state
    snapshot = PatientCaseSnapshot(
        user_id="user-1",
        profile_name="Test User",
    )

    from care_pilot.agent.orchestrator.agent import RoutingDecision

    async def mock_run_supervisor(*args, **kwargs):
        return RoutingDecision(
            next_agent="end",
            rationale="Interaction complete"
        )

    monkeypatch.setattr("care_pilot.features.companion.chat.workflows.companion_graph.run_supervisor_agent", mock_run_supervisor)

    graph = build_companion_graph().compile()

    initial_state: CompanionState = {
        "snapshot": snapshot,
        "messages": [HumanMessage(content="Hello")],
        "next_agent": None,
        "last_agent_response": None,
        "errors": [],
        "session_id": "session-1"
    }

    result = await graph.ainvoke(initial_state)

    assert result["next_agent"] == "end"


@pytest.mark.asyncio
async def test_companion_graph_routes_to_meal_and_back(monkeypatch) -> None:
    snapshot = PatientCaseSnapshot(
        user_id="user-1",
        profile_name="Test User",
    )

    from care_pilot.agent.orchestrator.agent import RoutingDecision

    # Sequence of decisions for the supervisor
    decisions = [
        RoutingDecision(next_agent="meal_agent", rationale="Analyzing meal"),
        RoutingDecision(next_agent="end", rationale="Done")
    ]

    call_count = 0
    async def mock_run_supervisor(*args, **kwargs):
        nonlocal call_count
        data = decisions[call_count]
        call_count += 1
        return data

    monkeypatch.setattr("care_pilot.features.companion.chat.workflows.companion_graph.run_supervisor_agent", mock_run_supervisor)

    # Mock ALL specialized agents to avoid real API calls
    async def mock_run_agent(request):
        return AgentResponse(
            agent_name="mock_agent",
            summary="Mock result",
            structured_output={},
        )

    monkeypatch.setattr("care_pilot.features.companion.chat.workflows.companion_graph.run_meal_agent", mock_run_agent)
    monkeypatch.setattr("care_pilot.features.companion.chat.workflows.companion_graph.run_medication_agent", mock_run_agent)
    monkeypatch.setattr("care_pilot.features.companion.chat.workflows.companion_graph.run_trend_agent", mock_run_agent)
    monkeypatch.setattr("care_pilot.features.companion.chat.workflows.companion_graph.run_adherence_agent", mock_run_agent)
    monkeypatch.setattr("care_pilot.features.companion.chat.workflows.companion_graph.run_care_plan_agent", mock_run_agent)

    graph = build_companion_graph().compile()

    initial_state: CompanionState = {
        "snapshot": snapshot,
        "messages": [HumanMessage(content="I ate laksa")],
        "next_agent": None,
        "last_agent_response": None,
        "errors": [],
        "session_id": "session-1"
    }

    result = await graph.ainvoke(initial_state)

    assert result["next_agent"] == "end"
    assert result["last_agent_response"].agent_name == "mock_agent"
