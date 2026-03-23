"""
Domain-level BaseAgent adapters for specialized non-AgentRequest agents.

These wrappers standardize outputs without altering existing behavior.
"""

from __future__ import annotations

from pydantic import BaseModel

from care_pilot.agent.core.base import AgentContext, AgentResult, BaseAgent
from care_pilot.agent.dietary.agent import analyze_dietary_request
from care_pilot.agent.dietary.schemas import DietaryAgentInput, DietaryAgentOutput
from care_pilot.agent.meal_analysis.arbitration import (
    MealLabelArbitrationDecision,
    arbitrate_meal_label,
)


class MealLabelArbitrationInput(BaseModel):
    vision_labels: list[str]
    claim_labels: list[str]
    user_text: str | None = None


class DietaryAgentAdapter(BaseAgent[DietaryAgentInput, DietaryAgentOutput]):
    name = "dietary_agent_adapter"
    input_schema = DietaryAgentInput
    output_schema = DietaryAgentOutput

    async def run(
        self, input_data: DietaryAgentInput, context: AgentContext
    ) -> AgentResult[DietaryAgentOutput]:
        output = await analyze_dietary_request(input_data)
        return AgentResult(
            success=True,
            agent_name="dietary_agent",
            output=output,
            confidence=None,
            rationale=output.analysis,
            warnings=list(output.warnings),
            errors=[],
            raw={
                "request_id": context.request_id,
                "correlation_id": context.correlation_id,
            },
        )


class MealLabelArbitrationAdapter(
    BaseAgent[MealLabelArbitrationInput, MealLabelArbitrationDecision | None]
):
    name = "meal_label_arbitration_adapter"
    input_schema = MealLabelArbitrationInput
    output_schema = MealLabelArbitrationDecision | None

    async def run(
        self, input_data: MealLabelArbitrationInput, context: AgentContext
    ) -> AgentResult[MealLabelArbitrationDecision | None]:
        decision = await arbitrate_meal_label(
            vision_labels=input_data.vision_labels,
            claim_labels=input_data.claim_labels,
            user_text=input_data.user_text,
        )
        return AgentResult(
            success=decision is not None,
            agent_name="meal_label_arbitration_agent",
            output=decision,
            confidence=decision.confidence if decision else None,
            rationale=decision.rationale if decision else None,
            warnings=[],
            errors=[] if decision else ["no_decision"],
            raw={
                "request_id": context.request_id,
                "correlation_id": context.correlation_id,
            },
        )


__all__ = [
    "DietaryAgentAdapter",
    "MealLabelArbitrationAdapter",
    "MealLabelArbitrationInput",
]
