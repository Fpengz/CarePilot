import os
from typing import Any, cast

import logfire
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.test import TestModel

from dietary_guardian.models.meal import MealEvent
from dietary_guardian.models.user import UserProfile
from dietary_guardian.safety.engine import SafetyEngine, SafetyViolation

load_dotenv()
logfire.configure(send_to_logfire=False)
logfire_api = cast(Any, logfire)

def get_model():
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return TestModel()
    os.environ.setdefault("GOOGLE_API_KEY", api_key)
    return GoogleModel("gemini-1.5-flash")


class AgentResponse(BaseModel):
    analysis: str
    advice: str
    is_safe: bool
    warnings: list[str] = []


dietary_agent = Agent(
    get_model(),
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


async def process_meal_request(user: UserProfile, meal: MealEvent) -> AgentResponse:
    with logfire_api.span("process_meal_request", user_id=user.id, meal_name=meal.name):
        safety_engine = SafetyEngine(user)

        try:
            # 1. Deterministic Safety Check
            warnings = safety_engine.validate_meal(meal)

            # 2. AI Reasoning (if safe)
            logfire_api.info("calling_dietary_agent", meal=meal.name)
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
