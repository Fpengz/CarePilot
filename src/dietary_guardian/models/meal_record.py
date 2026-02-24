from datetime import datetime, timezone

from pydantic import BaseModel, Field

from dietary_guardian.models.meal import MealState


class MealRecognitionRecord(BaseModel):
    id: str
    user_id: str
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    meal_state: MealState
    analysis_version: str = "v1"
    multi_item_count: int = 1
