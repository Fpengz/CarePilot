"""
Provide the multi-agent compatible care plan reasoning agent.

This agent synthesizes all available signals (meals, meds, trends, symptoms)
into a cohesive, clinician-aligned action plan for the patient.
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from care_pilot.agent.core.contracts import (
    AgentRecommendation,
    AgentRequest,
    AgentResponse,
)
from care_pilot.agent.runtime.llm_factory import LLMFactory
from care_pilot.config.llm import LLMCapability


class CarePlanAction(BaseModel):
    """A concrete health action for the user."""
    title: str
    description: str
    urgency: str


class CarePlanOutput(BaseModel):
    """The structured output of the CarePlanAgent."""
    headline: str
    summary: str
    reasoning: str
    actions: list[CarePlanAction] = Field(default_factory=list)


SYSTEM_PROMPT = (
    "You are the 'Care Strategy' Lead Specialist for CarePilot. "
    "Your role is to synthesize all signals in the Patient Case Snapshot into a cohesive, daily action plan."
    "\n\nStrategic Priorities:"
    "\n1. Acute Risks: Escalate immediately if symptoms or biomarkers suggest danger (e.g. very high BP)."
    "\n2. Adherence Gap: If doses were missed, prioritize a 'catch-up' or 'reset' strategy."
    "\n3. Nutritional Load: If sodium/sugar streaks are detected, provide a specific meal swap for the next turn."
    "\n4. Continuity: Reference previous turns to maintain a sense of a shared journey."
    "\n\nClinical Logic (Singapore Context):"
    "\n- For BP management, focus on lowering sodium in Hawker meals (e.g., swapping Laksa for sliced fish soup)."
    "\n- For diabetic patients, watch for high GI 'hidden' sugars in Kopi/Teh or snacks."
    "\n\nReturn strict JSON matching the CarePlanOutput schema."
)


def get_care_plan_agent() -> Agent[None, CarePlanOutput]:
    """Build the pydantic_ai agent instance."""
    model = LLMFactory.get_model(capability=LLMCapability.CHATBOT)
    return cast(
        Any,
        Agent(
            model,
            output_type=CarePlanOutput,
            system_prompt=SYSTEM_PROMPT,
        ),
    )


async def run_care_plan_agent(request: AgentRequest) -> AgentResponse:
    """Execute the care plan specialist agent."""
    agent = get_care_plan_agent()

    context_json = request.context.get("snapshot") or "{}"
    prompt = f"Develop a care strategy for the current patient state:\n{context_json}"

    result = await agent.run(prompt)
    plan = result.output

    recommendations = [
        AgentRecommendation(
            title=action.title,
            summary=action.description,
            priority="high" if action.urgency == "prompt" else "medium"
        )
        for action in plan.actions
    ]

    return AgentResponse(
        agent_name="care_plan_agent",
        status="success",
        summary=f"{plan.headline}: {plan.summary}",
        structured_output=plan.model_dump(),
        recommendations=recommendations,
        reasoning_trace=["Synthesized all blackboard signals", "Prioritized acute recovery actions"]
    )
