"""
Shadow-mode BaseAgent adapters for legacy AgentRequest/AgentResponse agents.

These adapters allow running existing agents via the BaseAgent/AgentResult
contract without changing production behavior.
"""

from __future__ import annotations

from care_pilot.agent.adherence.agent import run_adherence_agent
from care_pilot.agent.care_plan.agent import run_care_plan_agent
from care_pilot.agent.core.base import AgentContext, AgentResult, BaseAgent
from care_pilot.agent.core.contracts import AgentRequest, AgentResponse
from care_pilot.agent.emotion import EmotionAgent
from care_pilot.agent.emotion.schemas import (
    EmotionInferenceResult,
    EmotionSpeechAgentInput,
    EmotionTextAgentInput,
)
from care_pilot.agent.meal_analysis.agent import run_meal_agent
from care_pilot.agent.medication.agent import run_medication_agent
from care_pilot.agent.recommendation.agent import RecommendationAgent
from care_pilot.agent.trends.agent import run_trend_agent
from care_pilot.features.recommendations.domain.schemas import (
    RecommendationAgentInput,
    RecommendationAgentOutput,
)


class _AgentResponseAdapter(BaseAgent[AgentRequest, AgentResponse]):
    """Base adapter for AgentRequest/AgentResponse agents."""

    name: str
    input_schema = AgentRequest
    output_schema = AgentResponse

    async def _run_agent(self, input_data: AgentRequest) -> AgentResponse:
        raise NotImplementedError

    async def run(
        self, input_data: AgentRequest, context: AgentContext
    ) -> AgentResult[AgentResponse]:
        response = await self._run_agent(input_data)
        success = response.status == "success"
        return AgentResult(
            success=success,
            agent_name=response.agent_name,
            output=response,
            confidence=response.confidence,
            rationale=response.summary,
            warnings=[],
            errors=[] if success else [response.summary],
            raw={
                "request_id": context.request_id,
                "correlation_id": context.correlation_id,
                "agent_response": response.model_dump(mode="json"),
            },
        )


class TrendAgentAdapter(_AgentResponseAdapter):
    name = "trend_agent_adapter"

    async def _run_agent(self, input_data: AgentRequest) -> AgentResponse:
        return await run_trend_agent(input_data)


class CarePlanAgentAdapter(_AgentResponseAdapter):
    name = "care_plan_agent_adapter"

    async def _run_agent(self, input_data: AgentRequest) -> AgentResponse:
        return await run_care_plan_agent(input_data)


class MedicationAgentAdapter(_AgentResponseAdapter):
    name = "medication_agent_adapter"

    async def _run_agent(self, input_data: AgentRequest) -> AgentResponse:
        return await run_medication_agent(input_data)


class AdherenceAgentAdapter(_AgentResponseAdapter):
    name = "adherence_agent_adapter"

    async def _run_agent(self, input_data: AgentRequest) -> AgentResponse:
        return await run_adherence_agent(input_data)


class MealAgentAdapter(_AgentResponseAdapter):
    name = "meal_agent_adapter"

    async def _run_agent(self, input_data: AgentRequest) -> AgentResponse:
        return await run_meal_agent(input_data)


class EmotionTextAgentAdapter(BaseAgent[EmotionTextAgentInput, EmotionInferenceResult]):
    """BaseAgent wrapper for emotion text inference."""

    name = "emotion_text_agent_adapter"
    input_schema = EmotionTextAgentInput
    output_schema = EmotionInferenceResult

    def __init__(self, agent: EmotionAgent) -> None:
        self._agent = agent

    async def run(
        self, input_data: EmotionTextAgentInput, context: AgentContext
    ) -> AgentResult[EmotionInferenceResult]:
        result = await self._agent.infer_text(
            text=input_data.text,
            language=input_data.language,
            user_id=input_data.user_id,
        )
        return AgentResult(
            success=True,
            agent_name="emotion_agent",
            output=result,
            confidence=result.confidence,
            rationale=result.final_emotion,
            warnings=[],
            errors=[],
            raw={
                "request_id": context.request_id,
                "correlation_id": context.correlation_id,
            },
        )


class EmotionSpeechAgentAdapter(BaseAgent[EmotionSpeechAgentInput, EmotionInferenceResult]):
    """BaseAgent wrapper for emotion speech inference."""

    name = "emotion_speech_agent_adapter"
    input_schema = EmotionSpeechAgentInput
    output_schema = EmotionInferenceResult

    def __init__(self, agent: EmotionAgent) -> None:
        self._agent = agent

    async def run(
        self, input_data: EmotionSpeechAgentInput, context: AgentContext
    ) -> AgentResult[EmotionInferenceResult]:
        result = await self._agent.infer_speech(
            audio_bytes=input_data.audio_bytes,
            filename=input_data.filename,
            content_type=input_data.content_type,
            transcription=input_data.transcription,
            language=input_data.language,
            user_id=input_data.user_id,
        )
        return AgentResult(
            success=True,
            agent_name="emotion_agent",
            output=result,
            confidence=result.confidence,
            rationale=result.final_emotion,
            warnings=[],
            errors=[],
            raw={
                "request_id": context.request_id,
                "correlation_id": context.correlation_id,
            },
        )


class RecommendationAgentAdapter(BaseAgent[RecommendationAgentInput, RecommendationAgentOutput]):
    """BaseAgent wrapper for the recommendation agent."""

    name = "recommendation_agent_adapter"
    input_schema = RecommendationAgentInput
    output_schema = RecommendationAgentOutput

    def __init__(self, agent: RecommendationAgent, repository) -> None:
        self._agent = agent
        self._repository = repository

    async def run(
        self, input_data: RecommendationAgentInput, context: AgentContext
    ) -> AgentResult[RecommendationAgentOutput]:
        output = await self._agent.generate(input_data, repository=self._repository)
        return AgentResult(
            success=True,
            agent_name=self._agent.name,
            output=output,
            confidence=None,
            rationale="recommendation_generated",
            warnings=[],
            errors=[],
            raw={
                "request_id": context.request_id,
                "correlation_id": context.correlation_id,
            },
        )


__all__ = [
    "CarePlanAgentAdapter",
    "AdherenceAgentAdapter",
    "EmotionSpeechAgentAdapter",
    "EmotionTextAgentAdapter",
    "MealAgentAdapter",
    "MedicationAgentAdapter",
    "RecommendationAgentAdapter",
    "TrendAgentAdapter",
]
