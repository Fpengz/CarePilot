"""
Define the LangGraph-based companion orchestration graph.

This module implements the Supervisor-led multi-agent orchestration
using LangGraph and pydantic-ai agents.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict, cast

from langchain_core.messages import BaseMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from care_pilot.agent.adherence.agent import run_adherence_agent
from care_pilot.agent.care_plan.agent import run_care_plan_agent
from care_pilot.agent.core.contracts import AgentRequest, AgentResponse
from care_pilot.agent.meal_analysis.agent import run_meal_agent
from care_pilot.agent.medication.agent import run_medication_agent
from care_pilot.agent.orchestrator.agent import run_supervisor_agent
from care_pilot.agent.trends.agent import run_trend_agent
from care_pilot.features.companion.core.domain import PatientCaseSnapshot


class CompanionState(TypedDict):
    """The shared blackboard state for the companion LangGraph."""

    snapshot: PatientCaseSnapshot
    messages: Annotated[list[BaseMessage], add_messages]
    next_agent: str | None
    last_agent_response: AgentResponse | None
    errors: list[str]
    session_id: str


async def supervisor_node(state: CompanionState) -> dict[str, Any]:
    """Analyze state and decide which agent to call next."""
    user_msg = state["messages"][-1].content if state["messages"] else "No message"
    prompt = (
        f"User message: {user_msg}\n\n"
        f"Patient Snapshot: {state['snapshot'].model_dump_json(indent=2)}"
    )

    decision = await run_supervisor_agent(prompt)

    return {"next_agent": decision.next_agent}


def route_next(state: CompanionState) -> str:
    """Dynamic routing logic based on supervisor's decision."""
    next_agent = state.get("next_agent")
    if next_agent is None or next_agent == "end":
        return END
    return next_agent


# Specialist Nodes

async def meal_node(state: CompanionState) -> dict[str, Any]:
    """Execute the meal specialist agent."""
    user_msg = state["messages"][-1].content if state["messages"] else ""
    request = AgentRequest(
        user_id=state["snapshot"].user_id,
        session_id=state["session_id"],
        goal="Analyze meal from message",
        inputs={"text_context": str(user_msg)},
        context={"snapshot": state["snapshot"].model_dump_json()}
    )
    response = await run_meal_agent(request)
    return {"last_agent_response": response, "next_agent": "supervisor"}


async def medication_node(state: CompanionState) -> dict[str, Any]:
    """Execute the medication specialist agent."""
    user_msg = state["messages"][-1].content if state["messages"] else ""
    request = AgentRequest(
        user_id=state["snapshot"].user_id,
        session_id=state["session_id"],
        goal="Parse medication from message",
        inputs={"text_context": str(user_msg)},
        context={"snapshot": state["snapshot"].model_dump_json()}
    )
    response = await run_medication_agent(request)
    return {"last_agent_response": response, "next_agent": "supervisor"}


async def trend_node(state: CompanionState) -> dict[str, Any]:
    """Execute the trend specialist agent."""
    request = AgentRequest(
        user_id=state["snapshot"].user_id,
        session_id=state["session_id"],
        goal="Analyze health trends",
        context={"snapshot": state["snapshot"].model_dump_json()}
    )
    response = await run_trend_agent(request)
    return {"last_agent_response": response, "next_agent": "supervisor"}


async def adherence_node(state: CompanionState) -> dict[str, Any]:
    """Execute the adherence specialist agent."""
    request = AgentRequest(
        user_id=state["snapshot"].user_id,
        session_id=state["session_id"],
        goal="Analyze medication adherence",
        context={"snapshot": state["snapshot"].model_dump_json()}
    )
    response = await run_adherence_agent(request)
    return {"last_agent_response": response, "next_agent": "supervisor"}


async def care_plan_node(state: CompanionState) -> dict[str, Any]:
    """Execute the care plan specialist agent."""
    request = AgentRequest(
        user_id=state["snapshot"].user_id,
        session_id=state["session_id"],
        goal="Synthesize care plan",
        context={"snapshot": state["snapshot"].model_dump_json()}
    )
    response = await run_care_plan_agent(request)
    return {"last_agent_response": response, "next_agent": "supervisor"}


async def conversation_node(state: CompanionState) -> dict[str, Any]:  # noqa: ARG001
    """Placeholder for the conversation agent node."""
    # For now, end the loop after general conversation
    return {"next_agent": "end"}


def build_companion_graph() -> StateGraph:
    """Assemble the LangGraph state machine."""
    workflow = StateGraph(cast(Any, CompanionState))

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("meal_agent", meal_node)
    workflow.add_node("medication_agent", medication_node)
    workflow.add_node("trend_agent", trend_node)
    workflow.add_node("adherence_agent", adherence_node)
    workflow.add_node("care_plan_agent", care_plan_node)
    workflow.add_node("conversation_agent", conversation_node)

    workflow.add_edge(START, "supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        route_next,
        {
            "meal_agent": "meal_agent",
            "medication_agent": "medication_agent",
            "trend_agent": "trend_agent",
            "adherence_agent": "adherence_agent",
            "care_plan_agent": "care_plan_agent",
            "conversation_agent": "conversation_agent",
            END: END,
        },
    )

    workflow.add_edge("meal_agent", "supervisor")
    workflow.add_edge("medication_agent", "supervisor")
    workflow.add_edge("trend_agent", "supervisor")
    workflow.add_edge("adherence_agent", "supervisor")
    workflow.add_edge("care_plan_agent", "supervisor")
    workflow.add_edge("conversation_agent", "supervisor")

    return workflow
