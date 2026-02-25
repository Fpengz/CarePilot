from functools import lru_cache
from typing import Any, cast

import logfire
from pydantic import BaseModel
from pydantic_ai import Agent

from dietary_guardian.agents.provider_factory import LLMFactory, ModelProvider
from dietary_guardian.config.settings import get_settings
from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.meal import MealEvent
from dietary_guardian.models.user import UserProfile
from dietary_guardian.safety.engine import SafetyEngine, SafetyViolation

logfire.configure(send_to_logfire=False)
logfire_api = cast(Any, logfire)
logger = get_logger(__name__)

def get_model():
    settings = get_settings()
    provider = settings.llm_provider
    model_name = settings.gemini_model if provider == ModelProvider.GEMINI.value else None
    model = LLMFactory.get_model(provider=provider, model_name=model_name)
    logger.info("dietary_agent_model_destination %s", LLMFactory.describe_model_destination(model))
    return model


class AgentResponse(BaseModel):
    analysis: str
    advice: str
    is_safe: bool
    warnings: list[str] = []


@lru_cache(maxsize=1)
def get_dietary_agent() -> Agent[UserProfile, str]:
    model = get_model()
    return Agent(
        model,
        output_type=AgentResponse,
        deps_type=UserProfile,
        instrument=True,
        system_prompt=(
            "You are 'The Dietary Guardian', but everyone calls you 'Uncle Guardian'. "
            "You are a retired hawker who now helps other seniors stay healthy. "
            "Your tone is warm, empathetic, and uses Singaporean English (Singlish) naturally. "
            "Use words like 'Aiyah', 'Can lah', 'Don't play play', 'Uncle/Auntie' appropriately. "
            "If the food is dangerous (SafetyViolation), drop the humor and be firm but kind. "
            "Always encourage the 'Kampong Spirit'—remind them they are doing this for their family and neighbors."
        ),
    )


class _LazyDietaryAgentProxy:
    def __getattr__(self, item: str):
        return getattr(get_dietary_agent(), item)


dietary_agent = _LazyDietaryAgentProxy()


async def process_meal_request(user: UserProfile, meal: MealEvent) -> AgentResponse:
    with logfire_api.span("process_meal_request", user_id=user.id, meal_name=meal.name):
        safety_engine = SafetyEngine(user)
        dietary_agent = get_dietary_agent()
        destination = LLMFactory.describe_model_destination(getattr(dietary_agent, "model"))

        try:
            # 1. Deterministic Safety Check
            warnings = safety_engine.validate_meal(meal)

            # 2. AI Reasoning (if safe)
            logfire_api.info("calling_dietary_agent", meal=meal.name)
            logger.info(
                "dietary_agent_request user_id=%s meal=%s destination=%s",
                user.id,
                meal.name,
                destination,
            )
            result = await dietary_agent.run(
                f"Analyze this meal for {user.name}: {meal.model_dump_json()}", deps=user
            )

            response = result.output
            if not isinstance(response, AgentResponse):
                raise TypeError("Dietary agent returned unexpected output type.")
            response.warnings.extend(warnings)
            return response

        except SafetyViolation as e:
            logfire_api.error("safety_violation_intercepted", message=e.message)
            return AgentResponse(
                analysis="CRITICAL SAFETY TRIGGERED",
                advice=e.message,
                is_safe=False,
                warnings=[e.message],
            )
