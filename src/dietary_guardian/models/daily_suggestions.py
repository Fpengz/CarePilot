from typing import Literal

from pydantic import BaseModel, Field

MealSlot = Literal["breakfast", "lunch", "dinner", "snack"]


class DailySuggestionItem(BaseModel):
    slot: MealSlot
    title: str
    venue_type: str
    why_it_fits: list[str] = Field(default_factory=list)
    caution_notes: list[str] = Field(default_factory=list)
    confidence: float


class DailySuggestionBundle(BaseModel):
    locale: str
    generated_at: str
    data_sources: dict[str, object] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    suggestions: dict[str, DailySuggestionItem]

