"""Dietary agent that wraps safety checks and LLM meal analysis."""

from typing import Any, cast

import logfire
from pydantic import BaseModel

from dietary_guardian.config.settings import get_settings
from dietary_guardian.config.llm import LLMCapability
from dietary_guardian.llm import LLMFactory
from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.inference import InferenceModality, InferenceRequest
from dietary_guardian.models.meal import MealEvent
from dietary_guardian.models.user import UserProfile
from dietary_guardian.agents.executor import InferenceEngine
from dietary_guardian.safety.engine import SafetyEngine, SafetyViolation

logfire.configure(send_to_logfire=False)
logfire_api = cast(Any, logfire)
logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are 'The Dietary Guardian', but everyone calls you 'Uncle Guardian'. "
    "You are a retired hawker who now helps other seniors stay healthy. "
    "Your tone is warm, empathetic, and uses Singaporean English (Singlish) naturally. "
    "Use words like 'Aiyah', 'Can lah', 'Don't play play', 'Uncle/Auntie' appropriately. "
    "If the food is dangerous (SafetyViolation), drop the humor and be firm but kind. "
    "Always encourage the 'Kampong Spirit'—remind them they are doing this for their family and neighbors."
)


def get_model():
    model = LLMFactory.get_model(capability=LLMCapability.DIETARY_REASONING)
    logger.info("dietary_agent_model_destination %s", LLMFactory.describe_model_destination(model))
    return model


class AgentResponse(BaseModel):
    analysis: str
    advice: str
    is_safe: bool
    warnings: list[str] = []


class _DietaryAgentContract:
    _system_prompts = [SYSTEM_PROMPT]


dietary_agent = _DietaryAgentContract()


async def process_meal_request(user: UserProfile, meal: MealEvent) -> AgentResponse:
    with logfire_api.span("process_meal_request", user_id=user.id, meal_name=meal.name):
        safety_engine = SafetyEngine(user)
        engine = InferenceEngine(provider=get_settings().llm.provider, capability=LLMCapability.DIETARY_REASONING)
        try:
            warnings = safety_engine.validate_meal(meal)
            logger.info("dietary_agent_request user_id=%s meal=%s destination=%s", user.id, meal.name, engine.health().endpoint)
            request = InferenceRequest(
                request_id=f"dietary-{user.id}-{meal.timestamp.isoformat()}",
                user_id=user.id,
                modality=InferenceModality.TEXT,
                payload={"prompt": f"Analyze this meal for {user.name}: {meal.model_dump_json()}"},
                safety_context={"warnings": warnings},
                runtime_profile={"provider": engine.health().provider, "capability": LLMCapability.DIETARY_REASONING.value},
                trace_context={"meal_name": meal.name},
                output_schema=AgentResponse,
                system_prompt=SYSTEM_PROMPT,
            )
            result = await engine.infer(request)
            response = cast(AgentResponse, result.structured_output)
            response.warnings.extend(warnings)
            return response
        except SafetyViolation as exc:
            return AgentResponse(
                analysis="CRITICAL SAFETY TRIGGERED",
                advice=exc.message,
                is_safe=False,
                warnings=[exc.message],
            )
