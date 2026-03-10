"""Domain model for meal recognition records."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from dietary_guardian.domain.meals.models import EnrichedMealEvent, MealPerception, MealState


class MealRecognitionRecord(BaseModel):
    id: str
    user_id: str
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    meal_state: MealState
    meal_perception: MealPerception | None = None
    enriched_event: EnrichedMealEvent | None = None
    analysis_version: str = "v1"
    multi_item_count: int = 1
