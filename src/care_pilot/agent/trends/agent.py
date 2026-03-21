"""
Provide the multi-agent compatible trend reasoning agent.

This agent analyzes longitudinal health signals (biomarkers, meals, adherence)
to find patterns and suggest clinical next steps.
"""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from care_pilot.agent.core.contracts import (
    AgentAction,
    AgentRecommendation,
    AgentRequest,
    AgentResponse,
)
from care_pilot.agent.runtime.llm_factory import LLMFactory
from care_pilot.config.llm import LLMCapability


class TrendInsight(BaseModel):
    """Structured insight about a health trend."""
    metric: str
    pattern: Literal["improving", "stable", "worsening", "insufficient_data"]
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)


class TrendAnalysisOutput(BaseModel):
    """The output of the TrendAgent."""
    insights: list[TrendInsight] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"] = "low"
    rationale: str


SYSTEM_PROMPT = (
    "You are the 'Longitudinal Health' Specialist node. "
    "Your role is to analyze multi-day patterns in a patient's case snapshot. "
    "\n\nLook for correlations between:"
    "\n- Meal sodium/sugar and blood pressure trends."
    "\n- Medication adherence and biomarker changes (e.g., HbA1c, LDL)."
    "\n- Symptom clusters and activity logs."
    "\n\nReturn strict JSON matching the TrendAnalysisOutput schema."
)


def get_trend_agent() -> Agent[None, TrendAnalysisOutput]:
    """Build the pydantic_ai agent instance."""
    model = LLMFactory.get_model(capability=LLMCapability.CHATBOT)
    return cast(
        Any,
        Agent(
            model,
            output_type=TrendAnalysisOutput,
            system_prompt=SYSTEM_PROMPT,
        ),
    )


async def run_trend_agent(request: AgentRequest) -> AgentResponse:
    """Execute the trend specialist agent."""
    agent = get_trend_agent()

    # The trend agent primarily operates on the context (CaseSnapshot)
    context_json = request.context.get("snapshot") or "{}"
    prompt = f"Analyze health patterns for the following patient state:\n{context_json}"

    result = await agent.run(prompt)
    analysis = result.output

    recommendations = []
    actions = []

    for insight in analysis.insights:
        if insight.pattern == "worsening":
            recommendations.append(
                AgentRecommendation(
                    title=f"Worsening {insight.metric}",
                    summary=insight.summary,
                    priority="high"
                )
            )
            if analysis.risk_level == "high":
                actions.append(
                    AgentAction(
                        action_name="escalate_to_clinician",
                        params={"metric": insight.metric, "reason": insight.summary}
                    )
                )

    return AgentResponse(
        agent_name="trend_agent",
        status="success",
        summary=analysis.rationale,
        structured_output=analysis.model_dump(),
        recommendations=recommendations,
        actions=actions,
        reasoning_trace=["Analyzed longitudinal biomarker logs", "Correlated meals with risk flags"]
    )
