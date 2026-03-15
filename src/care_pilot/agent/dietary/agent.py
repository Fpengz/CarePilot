"""
Provide the dietary reasoning agent.

This agent delivers structured dietary guidance based on generic inputs.
"""

from __future__ import annotations

from typing import Any, cast

import logfire
from pydantic_ai import Agent

from care_pilot.agent.dietary.schemas import (
    DietaryAgentInput,
    DietaryAgentOutput,
)
from care_pilot.agent.runtime import LLMFactory
from care_pilot.config.llm import LLMCapability

logfire.configure(send_to_logfire=False)

SYSTEM_PROMPT = (
    "You are 'The CarePilot', but everyone calls you 'Uncle Guardian'. "
    "You are a retired hawker who now helps other seniors stay healthy. "
    "Your tone is warm, empathetic, and uses Singaporean English (Singlish) naturally. "
    "Use words like 'Aiyah', 'Can lah', 'Don't play play', 'Uncle/Auntie' appropriately. "
    "If the food is dangerous (is_safe=False), drop the humor and be firm but kind. "
    "Always encourage the 'Kampong Spirit'—remind them they are doing this for their family and neighbors."
)


def get_dietary_agent() -> Agent[None, DietaryAgentOutput]:
    """Build the pydantic_ai dietary reasoning agent."""
    model = LLMFactory.get_model(capability=LLMCapability.DIETARY_REASONING)
    return cast(
        Any,
        Agent(
            model,
            output_type=DietaryAgentOutput,
            system_prompt=SYSTEM_PROMPT,
        ),
    )


async def analyze_dietary_request(
    input_data: DietaryAgentInput,
) -> DietaryAgentOutput:
    """Run dietary reasoning against generic input."""
    agent = get_dietary_agent()
    prompt = (
        f"Analyze this meal for {input_data.user_name}:\n"
        f"Meal: {input_data.meal_name}\n"
        f"Ingredients: {', '.join(input_data.ingredients)}\n"
        f"Portion: {input_data.portion_size or 'Standard'}\n"
        f"Health Goals: {', '.join(input_data.health_goals)}\n"
        f"Dietary Restrictions: {', '.join(input_data.dietary_restrictions)}\n"
        f"Safety Status: {'Safe' if input_data.is_safe else 'UNSAFE'}\n"
        f"Safety Warnings: {', '.join(input_data.safety_warnings)}"
    )
    result = await agent.run(prompt)
    return result.output
