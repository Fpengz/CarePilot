"""
Provide the supervisor orchestrator agent.

This agent decides which specialist agent should handle the next turn.
"""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from care_pilot.agent.runtime import LLMFactory
from care_pilot.config.llm import LLMCapability


class RoutingDecision(BaseModel):
    """The decision made by the Supervisor agent."""

    next_agent: Literal[
        "meal_agent",
        "medication_agent",
        "trend_agent",
        "adherence_agent",
        "care_plan_agent",
        "conversation_agent",
        "end",
    ]
    rationale: str = Field(description="Explanation for routing to the chosen agent.")


def get_supervisor_agent() -> Agent[None, RoutingDecision]:
    """Build the pydantic_ai supervisor agent."""
    model = LLMFactory.get_model(capability=LLMCapability.CHATBOT)
    return cast(
        Any,
        Agent(
            model,
            output_type=RoutingDecision,
            system_prompt=(
                "You are the Supervisor Orchestrator for CarePilot, an AI Health Companion. "
                "Your job is to analyze the user's intent and the current patient snapshot, "
                "then route the request to the correct specialist agent. "
                "\n\nSpecialists:"
                "\n- meal_agent: For identifying food, estimating nutrition, or logging meals."
                "\n- medication_agent: For understanding prescriptions or medication intake."
                "\n- trend_agent: For longitudinal pattern analysis across meals/meds/biomarkers."
                "\n- adherence_agent: For medication behavior analysis and nudge strategy."
                "\n- care_plan_agent: For generating actionable health advice and next steps."
                "\n- conversation_agent: For general chat, empathy, or clarifying questions."
                "\n\nRoute to 'end' only if the interaction is complete or requires no further specialist work."
            ),
        ),
    )


async def run_supervisor_agent(prompt: str) -> RoutingDecision:
    """Execute the supervisor agent node logic."""
    agent = get_supervisor_agent()
    result = await agent.run(prompt)
    return result.output
