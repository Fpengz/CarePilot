"""
Provide the recommendation agent.

This module provides recommendation synthesis.
"""

from __future__ import annotations

from care_pilot.features.recommendations.domain.engine import generate_daily_agent_recommendation
from care_pilot.features.recommendations.domain.schemas import (
    RecommendationAgentInput,
    RecommendationAgentOutput,
)


class RecommendationAgent:
    """Agent facade for recommendation synthesis."""

    name = "recommendation_agent"

    async def generate(
        self,
        input_data: RecommendationAgentInput,
        repository,
    ) -> RecommendationAgentOutput:
        """Synthesize a daily recommendation bundle."""
        recommendation = generate_daily_agent_recommendation(
            repository=repository,
            user_id=input_data.user_id,
            health_profile=input_data.health_profile,
            user_profile=input_data.user_profile,
            meal_history=input_data.meal_history,
            clinical_snapshot=input_data.clinical_snapshot,
        )
        return RecommendationAgentOutput(recommendation=recommendation)


async def generate_recommendations(
    input_data: RecommendationAgentInput,
    repository,
) -> RecommendationAgentOutput:
    """Synthesize a daily recommendation bundle (functional entrypoint)."""
    agent = RecommendationAgent()
    return await agent.generate(input_data, repository)
