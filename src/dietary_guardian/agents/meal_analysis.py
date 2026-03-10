"""Canonical meal analysis agent layered on top of the hawker vision module."""

from __future__ import annotations

from typing import Any

from dietary_guardian.agents.base import AgentContext, AgentResult, BaseAgent
from dietary_guardian.agents.schemas import MealAnalysisAgentInput, MealAnalysisAgentOutput
from dietary_guardian.agents.vision import HawkerVisionModule


class MealAnalysisAgent(BaseAgent[MealAnalysisAgentInput, MealAnalysisAgentOutput]):
    """Agent facade for meal perception, normalization, and persistence."""

    name = "meal_analysis_agent"
    input_schema = MealAnalysisAgentInput
    output_schema = MealAnalysisAgentOutput

    def __init__(
        self,
        provider: str | None = None,
        model_name: str | None = None,
        *,
        local_profile: Any | None = None,
        food_store: Any | None = None,
    ) -> None:
        self._module = HawkerVisionModule(
            provider=provider,
            model_name=model_name,
            local_profile=local_profile,
            food_store=food_store,
        )

    async def run(
        self,
        input_data: MealAnalysisAgentInput,
        context: AgentContext,
    ) -> AgentResult[MealAnalysisAgentOutput]:
        user_id = input_data.user_id or context.user_id
        if input_data.persist_record:
            if user_id is None:
                raise ValueError("meal analysis persistence requires a user_id")
            vision_result, meal_record = await self._module.analyze_and_record(
                input_data.image_input,
                user_id,
                request_id=input_data.request_id or context.request_id,
                correlation_id=input_data.correlation_id or context.correlation_id,
            )
        else:
            vision_result = await self._module.analyze_dish(
                input_data.image_input,
                user_id=user_id,
                request_id=input_data.request_id or context.request_id,
                correlation_id=input_data.correlation_id or context.correlation_id,
            )
            meal_record = None
        return AgentResult(
            success=True,
            agent_name=self.name,
            output=MealAnalysisAgentOutput(
                vision_result=vision_result,
                meal_record=meal_record,
            ),
            confidence=float(vision_result.primary_state.confidence_score),
            raw=vision_result.model_dump(mode="json"),
        )

    async def analyze_and_record(
        self,
        image_input: Any,
        user_id: str,
        request_id: str | None = None,
        correlation_id: str | None = None,
    ):
        return await self._module.analyze_and_record(
            image_input,
            user_id,
            request_id=request_id,
            correlation_id=correlation_id,
        )
