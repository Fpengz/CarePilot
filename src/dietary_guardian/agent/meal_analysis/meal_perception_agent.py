"""
Provide the meal perception agent.

This agent uses computer vision to identify foods in images.
"""

from __future__ import annotations

import time
from typing import Any, cast

from pydantic_ai import Agent

from dietary_guardian.agent.meal_analysis.schemas import (
    MealAnalysisAgentInput,
    MealAnalysisAgentOutput,
    MealPerception,
)
from dietary_guardian.agent.runtime import LLMFactory
from dietary_guardian.config.llm import LLMCapability

SYSTEM_PROMPT = (
    "You are the 'Hawker Vision' Expert, a specialized AI for Singaporean cuisine. "
    "Your role is perception only. Return strict JSON matching the MealPerception schema. "
    "Detect likely foods, component count, candidate aliases, coarse portion estimates, "
    "visible preparation cues, image quality, confidence, and uncertainty. "
    "image_quality must be one of: poor, fair, good, unknown (string only). "
    "items must be an array; do not return an object for items. "
    "Do not estimate nutrition, do not produce risk tags, and do not give advice."
)


def get_meal_perception_agent() -> Agent[None, MealPerception]:
    """Build the pydantic_ai meal perception agent."""
    model = LLMFactory.get_model(capability=LLMCapability.MEAL_VISION)
    return cast(
        Any,
        Agent(
            model,
            output_type=MealPerception,
            system_prompt=SYSTEM_PROMPT,
        ),
    )


async def analyze_meal_perception(input_data: MealAnalysisAgentInput) -> MealAnalysisAgentOutput:
    """Run meal perception against image or text context."""
    started = time.perf_counter()
    agent = get_meal_perception_agent()

    # Build prompt/message based on input
    prompt = "Analyze the provided input and generate a MealPerception."
    if input_data.text_context:
        prompt = f"{prompt} Context: {input_data.text_context}"

    # pydantic_ai handle images via dependencies or model calls if the model supports it.
    # For now, we'll pass the prompt. If images are needed, we'd use model-specific multi-modal inputs.
    # LLMFactory returns models that should handle this if configured.

    result = await agent.run(prompt)
    elapsed = (time.perf_counter() - started) * 1000.0

    return MealAnalysisAgentOutput(
        perception=result.output,
        raw_output=str(result.output),
        latency_ms=elapsed,
    )
