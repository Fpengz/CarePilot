"""Input contracts for the dietary reasoning agent."""

from pydantic import BaseModel

from dietary_guardian.domain.identity.models import UserProfile
from dietary_guardian.models.meal import MealEvent


class DietaryAgentInput(BaseModel):
    """Typed input for dietary safety and reasoning requests."""

    user: UserProfile
    meal: MealEvent
