"""
Provide the multi-agent compatible meal perception agent.

This agent implements the reasoning/perception layer for meal analysis,
adhering to the shared AgentRequest/AgentResponse contracts.
"""

from __future__ import annotations

import time
from typing import Any, cast

from pydantic_ai import Agent

from care_pilot.agent.core.contracts import AgentRecommendation, AgentRequest, AgentResponse
from care_pilot.agent.meal_analysis.schemas import (
    MealAnalysisAgentInput,
    MealAnalysisAgentOutput,
    MealPerception,
)
from care_pilot.agent.runtime.llm_factory import LLMFactory
from care_pilot.config.llm import LLMCapability
from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are the 'Hawker Vision' Specialist node in a multi-agent care system. "
    "Your role is to perceive and interpret meal inputs (text or images) for Singaporean cuisine. "
    "\n\nReturn strict JSON matching the MealPerception schema. "
    "\nDetect: likely foods, component count, portion estimates, preparation cues, image quality."
    "\n\nDo NOT estimate nutrition, do NOT produce clinical advice."
)


def get_meal_agent() -> Agent[None, MealPerception]:
    """Build the pydantic_ai agent instance."""
    model = LLMFactory.get_model(capability=LLMCapability.MEAL_VISION)
    return cast(
        Any,
        Agent(
            model,
            output_type=MealPerception,
            system_prompt=SYSTEM_PROMPT,
        ),
    )


async def run_meal_agent(request: AgentRequest) -> AgentResponse:
    """Execute the meal specialist agent."""
    logger.info("run_meal_agent_start correlation_id=%s", request.correlation_id)
    agent = get_meal_agent()

    # Extract input
    text_input = request.inputs.get("text_context") or request.goal

    result = await agent.run(text_input)
    perception = result.output

    recommendations = []
    if not perception.meal_detected:
        recommendations.append(
            AgentRecommendation(
                title="Clarify Meal",
                summary="The AI couldn't identify a clear meal. Please provide more detail or a better photo.",
                priority="high",
            )
        )
    elif perception.confidence_score < 0.7:
        recommendations.append(
            AgentRecommendation(
                title="Low Confidence",
                summary=f"Only {int(perception.confidence_score * 100)}% sure about this meal. Confirmation required.",
                priority="medium",
            )
        )

    return AgentResponse(
        agent_name="meal_agent",
        status="success" if perception.meal_detected else "blocked",
        summary=f"Perceived {len(perception.items)} items with confidence {perception.confidence_score:.2f}.",
        structured_output=perception.model_dump(),
        recommendations=recommendations,
        confidence=perception.confidence_score,
        reasoning_trace=["Analyzed image/text context", "Extracted meal components"],
    )


async def analyze_meal_perception(
    input_data: MealAnalysisAgentInput,
) -> MealAnalysisAgentOutput:
    """Run meal perception against image or text context. (Legacy entry point)"""
    started = time.perf_counter()
    agent = get_meal_agent()

    # Build prompt/message based on input
    prompt = "Analyze the provided input and generate a MealPerception."
    if input_data.text_context:
        prompt = f"{prompt} Context: {input_data.text_context}"

    result = await agent.run(prompt)
    elapsed = (time.perf_counter() - started) * 1000.0

    return MealAnalysisAgentOutput(
        perception=result.output,
        raw_output=str(result.output),
        latency_ms=elapsed,
    )
