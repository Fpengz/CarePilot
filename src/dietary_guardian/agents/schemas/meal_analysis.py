"""Input and output contracts for meal analysis agents."""

from pydantic import BaseModel

from dietary_guardian.models.meal import ImageInput, VisionResult
from dietary_guardian.models.meal_record import MealRecognitionRecord


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
