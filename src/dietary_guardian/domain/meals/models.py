from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ImageQuality = Literal["poor", "fair", "good", "unknown"]
MatchStrategy = Literal["exact_alias", "partial_alias", "fuzzy_alias", "fallback_label", "unmatched"]


class MealNutritionProfile(BaseModel):
    calories: float = Field(default=0.0, ge=0.0, description="kcal")
    carbs_g: float = Field(default=0.0, ge=0.0)
    sugar_g: float = Field(default=0.0, ge=0.0)
    protein_g: float = Field(default=0.0, ge=0.0)
    fat_g: float = Field(default=0.0, ge=0.0)
    sodium_mg: float = Field(default=0.0, ge=0.0)
    fiber_g: float = Field(default=0.0, ge=0.0)

    @classmethod
    def from_legacy(cls, value: object) -> MealNutritionProfile:
        from dietary_guardian.models.meal import Nutrition

        if isinstance(value, cls):
            return value
        if isinstance(value, Nutrition):
            return cls(
                calories=float(value.calories),
                carbs_g=float(value.carbs_g),
                sugar_g=float(value.sugar_g),
                protein_g=float(value.protein_g),
                fat_g=float(value.fat_g),
                sodium_mg=float(value.sodium_mg),
                fiber_g=float(value.fiber_g or 0.0),
            )
        return cls.model_validate(value)

    def to_legacy(self):
        from dietary_guardian.models.meal import Nutrition

        return Nutrition(
            calories=self.calories,
            carbs_g=self.carbs_g,
            sugar_g=self.sugar_g,
            protein_g=self.protein_g,
            fat_g=self.fat_g,
            sodium_mg=self.sodium_mg,
            fiber_g=self.fiber_g,
        )


class MealPortionEstimate(BaseModel):
    amount: float = Field(default=1.0, ge=0.0)
    unit: str = "serving"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class PortionReference(BaseModel):
    unit: str
    grams: float = Field(default=0.0, ge=0.0)
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)


class RawFoodSourceRecord(BaseModel):
    source_name: str
    source_id: str
    source_path: str | None = None


class PerceivedMealItem(BaseModel):
    label: str
    candidate_aliases: list[str] = Field(default_factory=list)
    detected_components: list[str] = Field(default_factory=list)
    portion_estimate: MealPortionEstimate = Field(default_factory=MealPortionEstimate)
    preparation: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class MealPerception(BaseModel):
    meal_detected: bool = True
    items: list[PerceivedMealItem] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    image_quality: ImageQuality = "unknown"
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)


class NormalizedMealItem(BaseModel):
    detected_label: str
    canonical_food_id: str | None = None
    canonical_name: str
    matched_alias: str | None = None
    match_strategy: MatchStrategy = "unmatched"
    match_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    preparation: str | None = None
    portion_estimate: MealPortionEstimate = Field(default_factory=MealPortionEstimate)
    estimated_grams: float | None = Field(default=None, ge=0.0)
    nutrition: MealNutritionProfile = Field(default_factory=MealNutritionProfile)
    risk_tags: list[str] = Field(default_factory=list)
    source_dataset: str | None = None


class EnrichedMealEvent(BaseModel):
    meal_name: str
    normalized_items: list[NormalizedMealItem] = Field(default_factory=list)
    total_nutrition: MealNutritionProfile = Field(default_factory=MealNutritionProfile)
    risk_tags: list[str] = Field(default_factory=list)
    unresolved_items: list[str] = Field(default_factory=list)
    source_records: list[RawFoodSourceRecord] = Field(default_factory=list)
    needs_manual_review: bool = False
    summary: str | None = None
