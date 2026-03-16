"""
Define meal recognition records.

This module contains domain models for meal recognition results.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from care_pilot.features.meals.domain.models import (
    EnrichedMealEvent,
    MealPerception,
    MealState,
)


class MealRecognitionRecord(BaseModel):
    id: str
    user_id: str
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str
    meal_state: MealState
    meal_perception: MealPerception | None = None
    enriched_event: EnrichedMealEvent | None = None
    analysis_version: str = "v1"
    multi_item_count: int = 1
