"""Canonical recommendation agent for daily plan synthesis."""

from __future__ import annotations

from dietary_guardian.capabilities.base import AgentContext, AgentResult, BaseAgent
from dietary_guardian.domain.recommendations.schemas import RecommendationAgentInput, RecommendationAgentOutput
from dietary_guardian.domain.recommendations.engine import (
    generate_daily_agent_recommendation,
)


class RecommendationAgent(BaseAgent[RecommendationAgentInput, RecommendationAgentOutput]):
    """Agent facade over daily recommendation synthesis logic."""

    name = "recommendation_agent"
    input_schema = RecommendationAgentInput
    output_schema = RecommendationAgentOutput

    def generate(
        self,
        input_data: RecommendationAgentInput,
        *,
        repository,
    ) -> RecommendationAgentOutput:
        """Synchronously synthesize a daily recommendation bundle."""

        recommendation = generate_daily_agent_recommendation(
            repository=repository,
            user_id=input_data.user_id,
            health_profile=input_data.health_profile,
            user_profile=input_data.user_profile,
            meal_history=input_data.meal_history,
            clinical_snapshot=input_data.clinical_snapshot,
        )
        return RecommendationAgentOutput(recommendation=recommendation)

    async def run(
        self,
        input_data: RecommendationAgentInput,
        context: AgentContext,
    ) -> AgentResult[RecommendationAgentOutput]:
        output = self.generate(input_data, repository=context.metadata["repository"])
        recommendation = output.recommendation
        confidences = [
            card.confidence
            for card in recommendation.recommendations.values()
            if card.confidence is not None
        ]
        confidence = round(sum(confidences) / len(confidences), 4) if confidences else None
        return AgentResult(
            success=True,
            agent_name=self.name,
            output=output,
            confidence=confidence,
            raw=recommendation.model_dump(mode="json"),
        )
