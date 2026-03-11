"""Agent I/O schemas for meal analysis and dietary reasoning — pure domain contracts."""

from __future__ import annotations

from pydantic import BaseModel

from dietary_guardian.domain.identity.models import UserProfile
from dietary_guardian.domain.meals.models import ImageInput, MealEvent, VisionResult
from dietary_guardian.domain.meals.recognition import MealRecognitionRecord


class DietaryAgentInput(BaseModel):
    """Typed input for dietary safety and reasoning requests."""

    user: UserProfile
    meal: MealEvent


class MealAnalysisAgentInput(BaseModel):
    """Payload for meal analysis from image or text context."""

    image_input: ImageInput | str
    user_id: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    persist_record: bool = True


class MealAnalysisAgentOutput(BaseModel):
    """Output envelope for meal analysis runs."""

    vision_result: VisionResult
    meal_record: MealRecognitionRecord | None = None


__all__ = ["DietaryAgentInput", "MealAnalysisAgentInput", "MealAnalysisAgentOutput"]
