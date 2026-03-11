"""Domain models and helpers for meals."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

ImageQuality = Literal["poor", "fair", "good", "unknown"]
MatchStrategy = Literal["exact_alias", "partial_alias", "fuzzy_alias", "fallback_label", "unmatched"]


# ---------------------------------------------------------------------------
# Nutrition value types (previously in models/meal.py)
# ---------------------------------------------------------------------------

class GlycemicIndexLevel(StrEnum):
    LOW = "Low (<55)"
    MEDIUM = "Medium (56-69)"
    HIGH = "High (>70)"
    UNKNOWN = "Unknown"


class PortionSize(StrEnum):
    SMALL = "Small (e.g., half bowl)"
    STANDARD = "Standard (e.g., full bowl)"
    LARGE = "Large (e.g., upsized)"
    FAMILY = "Family Share"


class Ingredient(BaseModel):
    name: str
    amount_g: float | None = None
    is_hidden: bool = Field(default=False, description="e.g., sugar in gravy, hidden lard")
    allergen_info: list[str] | None = Field(default_factory=list)


class Nutrition(BaseModel):
    calories: float = Field(..., ge=0, description="kcal")
    carbs_g: float = Field(..., ge=0)
    sugar_g: float = Field(..., ge=0)
    protein_g: float = Field(..., ge=0)
    fat_g: float = Field(..., ge=0)
    sodium_mg: float = Field(..., ge=0)
    fiber_g: float | None = Field(default=0.0, ge=0)


class LocalizationDetails(BaseModel):
    """Captures the specific cultural nuance of the dish."""

    dialect_name: str | None = Field(None, description="e.g., 'Char Kway Teow' (Hokkien)")
    variant: str | None = Field(None, description="e.g., 'Penang Style' vs 'Singapore Style'")
    detected_components: list[str] = Field(
        default_factory=list,
        description="Specific local ingredients found e.g., 'Hum' (Cockles), 'Lard Cubes'",
    )


class SafetyAnalysis(BaseModel):
    is_safe_for_consumption: bool = True
    risk_factors: list[str] = Field(default_factory=list, description="e.g., 'High Sodium', 'High Sugar'")
    diabetic_warning: bool = False
    hypertensive_warning: bool = False


class MealState(BaseModel):
    """The 'Gold Standard' output for the Hawker Vision Module."""

    dish_name: str = Field(..., description="Standardized English name")
    confidence_score: float = Field(..., ge=0, le=1, description="Model's confidence in identification")
    identification_method: Literal["AI_Flash", "HPB_Fallback", "User_Manual"]
    ingredients: list[Ingredient]
    nutrition: Nutrition
    portion_size: PortionSize = PortionSize.STANDARD
    glycemic_index_estimate: GlycemicIndexLevel = GlycemicIndexLevel.UNKNOWN
    localization: LocalizationDetails = Field(default_factory=LocalizationDetails)
    visual_anomalies: list[str] = Field(
        default_factory=list,
        description="e.g., 'Excessive oil sheen', 'Gravy separation'",
    )
    suggested_modifications: list[str] = Field(
        default_factory=list,
        description="Actionable advice e.g., 'Ask for less gravy'",
    )


class MealEvent(BaseModel):
    """Simplified meal representation for user input or manual logging."""

    name: str
    ingredients: list[Ingredient] = Field(default_factory=list)
    nutrition: Nutrition
    timestamp: datetime = Field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Domain perception and enrichment models
# ---------------------------------------------------------------------------

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

    def to_legacy(self) -> Nutrition:
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


class VisionResult(BaseModel):
    """Wrapper for the vision pipeline result."""

    primary_state: MealState
    perception: MealPerception | None = None
    enriched_event: EnrichedMealEvent | None = None
    raw_ai_output: str
    needs_manual_review: bool = False
    processing_latency_ms: float = 0.0
    model_version: str = "gemini-flash-1.5"


class ImageInput(BaseModel):
    source: Literal["upload", "camera"]
    filename: str | None = None
    mime_type: str
    content: bytes
    metadata: dict[str, str] = Field(default_factory=dict)
