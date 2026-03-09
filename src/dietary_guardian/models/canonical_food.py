from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from dietary_guardian.domain.meals import PortionReference
from dietary_guardian.models.meal import Nutrition
from dietary_guardian.models.recommendation_agent import MealSlot


class CanonicalFoodAlternative(BaseModel):
    name_en: str
    name_cn: str | None = None
    benefit: str


class CanonicalFoodAdvice(BaseModel):
    cn: str | None = None
    en: str
    risk_level: str | None = None


class CanonicalFoodRecord(BaseModel):
    food_id: str
    title: str
    locale: str = "en-SG"
    aliases: list[str] = Field(default_factory=list)
    aliases_normalized: list[str] = Field(default_factory=list)
    slot: MealSlot
    venue_type: str
    cuisine_tags: list[str] = Field(default_factory=list)
    ingredient_tags: list[str] = Field(default_factory=list)
    preparation_tags: list[str] = Field(default_factory=list)
    nutrition: Nutrition
    price_tier: Literal["budget", "moderate", "flexible"] = "moderate"
    health_tags: list[str] = Field(default_factory=list)
    risk_tags: list[str] = Field(default_factory=list)
    glycemic_index_label: str | None = None
    glycemic_index_value: int | None = None
    disease_advice: dict[str, CanonicalFoodAdvice] = Field(default_factory=dict)
    alternatives: list[CanonicalFoodAlternative] = Field(default_factory=list)
    serving_size: str | None = None
    default_portion_grams: float | None = None
    portion_references: list[PortionReference] = Field(default_factory=list)
    source_dataset: str = "internal"
    source_type: str = "seed"
    localization_variant: str | None = None
    active: bool = True

    @property
    def meal_id(self) -> str:
        return self.food_id
