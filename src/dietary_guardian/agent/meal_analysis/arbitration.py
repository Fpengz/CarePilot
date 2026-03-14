"""
Meal label arbitration helpers.

This module resolves conflicts between vision labels and user-claimed meal text
using pydantic_ai.
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from dietary_guardian.agent.runtime import LLMFactory
from dietary_guardian.config.llm import LLMCapability


class MealLabelArbitrationDecision(BaseModel):
    """Structured decision for meal label arbitration."""

    chosen_label: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale: str | None = None


SYSTEM_PROMPT = (
    "You are a reconciliation arbiter. Choose the most plausible food label based on evidence. "
    "Return strict JSON with chosen_label, confidence, rationale."
)


def get_arbitration_agent() -> Agent[None, MealLabelArbitrationDecision]:
    """Build the pydantic_ai meal label arbitration agent."""
    model = LLMFactory.get_model(capability=LLMCapability.DIETARY_REASONING)
    return cast(
        Any,
        Agent(
            model,
            output_type=MealLabelArbitrationDecision,
            system_prompt=SYSTEM_PROMPT,
        ),
    )


async def arbitrate_meal_label(
    *,
    vision_labels: list[str],
    claim_labels: list[str],
    user_text: str | None,
) -> MealLabelArbitrationDecision | None:
    """Resolve a single best label when vision and user claims disagree."""
    if not user_text or not vision_labels or not claim_labels:
        return None

    agent = get_arbitration_agent()
    prompt = (
        f"Vision labels: {vision_labels}\n"
        f"User claims: {claim_labels}\n"
        f"User text: {user_text}\n"
        "Select the best single label. If uncertain, choose the most specific plausible label."
    )
    try:
        result = await agent.run(prompt)
        return result.output
    except Exception:  # noqa: BLE001
        return None


__all__ = ["MealLabelArbitrationDecision", "arbitrate_meal_label"]
