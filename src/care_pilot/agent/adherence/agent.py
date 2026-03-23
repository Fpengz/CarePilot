"""
Provide the multi-agent compatible medication adherence reasoning agent.

This agent reasons about medication-taking behavior, detects missed doses,
and proposes personalized nudge strategies.
"""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import BaseModel
from pydantic_ai import Agent

from care_pilot.agent.core.contracts import AgentRecommendation, AgentRequest, AgentResponse
from care_pilot.agent.runtime.llm_factory import LLMFactory
from care_pilot.config.llm import LLMCapability
from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)


class AdherenceAnalysisOutput(BaseModel):
    """The structured output of the AdherenceAgent."""

    adherence_status: Literal["excellent", "good", "concerning", "critical"]
    missed_dose_pattern: str | None = None
    suggested_nudge_strategy: str
    rationale: str


SYSTEM_PROMPT = (
    "You are the 'Medication Adherence' Specialist for CarePilot. "
    "Your goal is to detect patterns in medication-taking behavior and propose empathetic, "
    "culturally relevant nudge strategies for a Singaporean patient context."
    "\n\nContextual Reasoning:"
    "\n- If adherence is low, correlate it with emotion signals (stress, frustration) or meal patterns (skipping lunch)."
    "\n- Missed doses during 'Hawker Culture' heavy times (lunch/dinner) might suggest logistical barriers."
    "\n- Use 'family-centered' or 'longevity-focused' appeals for older patients."
    "\n\nNudge Strategies:"
    "\n- empathetic: 'It's okay to miss a dose, let's get back on track with your next meal.'"
    "\n- logistical: 'Try keeping your Metformin near your favorite coffee mug.'"
    "\n- family: 'Staying consistent helps you keep active for your weekend family gatherings.'"
    "\n\nReturn strict JSON matching the AdherenceAnalysisOutput schema."
)


def get_adherence_agent() -> Agent[None, AdherenceAnalysisOutput]:
    """Build the pydantic_ai agent instance."""
    model = LLMFactory.get_model(capability=LLMCapability.CHATBOT)
    return cast(
        Any,
        Agent(
            model,
            output_type=AdherenceAnalysisOutput,
            system_prompt=SYSTEM_PROMPT,
        ),
    )


async def run_adherence_agent(request: AgentRequest) -> AgentResponse:
    """Execute the adherence specialist agent."""
    logger.info("run_adherence_agent_start correlation_id=%s", request.correlation_id)
    agent = get_adherence_agent()

    context_json = request.context.get("snapshot") or "{}"
    prompt = f"Analyze medication adherence for the current patient state:\n{context_json}"

    result = await agent.run(prompt)
    analysis = result.output

    recommendations = [
        AgentRecommendation(
            title="Adherence Strategy",
            summary=analysis.suggested_nudge_strategy,
            priority="high"
            if analysis.adherence_status in ("concerning", "critical")
            else "medium",
        )
    ]

    return AgentResponse(
        agent_name="adherence_agent",
        status="success",
        summary=f"Status is {analysis.adherence_status}. {analysis.rationale}",
        structured_output=analysis.model_dump(),
        recommendations=recommendations,
        reasoning_trace=[
            "Analyzed adherence events from snapshot",
            "Evaluated behavioral triggers",
        ],
    )
