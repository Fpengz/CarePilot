"""
Normalize meal perception results into domain models.

This module bridges the gap between raw agent perception and the structured
meal domain models, including food store matching and portion estimation.
"""

from __future__ import annotations

from care_pilot.features.meals.domain.models import (
    GlycemicIndexLevel,
    Ingredient,
    MealState,
    MealPerception,
    Nutrition,
    PortionSize,
    VisionResult,
)


def perception_to_meal_state(perception: MealPerception) -> MealState:
    """Map generic agent perception to the initial legacy MealState."""
    primary_item = perception.items[0] if perception.items else None
    amount = primary_item.portion_estimate.amount if primary_item is not None else 1.0
    portion_size = (
        PortionSize.SMALL
        if amount <= 0.75
        else PortionSize.LARGE
        if amount >= 1.5
        else PortionSize.STANDARD
    )
    return MealState(
        dish_name=(primary_item.label if primary_item is not None else "Unidentified meal"),
        confidence_score=perception.confidence_score,
        identification_method="AI_Flash",
        ingredients=[Ingredient(name=item.label) for item in perception.items[:8]],
        nutrition=Nutrition(calories=0, carbs_g=0, sugar_g=0, protein_g=0, fat_g=0, sodium_mg=0),
        portion_size=portion_size,
        glycemic_index_estimate=GlycemicIndexLevel.UNKNOWN,
        visual_anomalies=list(perception.uncertainties),
    )


def build_clarification_response(
    reason: str,
    confidence_score: float = 0.0,
    latency_ms: float = 0.0,
    model_version: str = "unknown",
) -> VisionResult:
    """Build a domain VisionResult for cases where clarification is needed."""
    state = MealState(
        dish_name="Clarification Required",
        confidence_score=confidence_score,
        identification_method="User_Manual",
        ingredients=[],
        nutrition=Nutrition(calories=0, carbs_g=0, sugar_g=0, protein_g=0, fat_g=0, sodium_mg=0),
        visual_anomalies=["Image uncertainty"],
        suggested_modifications=[
            "Clarification needed: please retake the photo with better lighting.",
            "Clarification needed: capture the whole dish from top-down angle.",
        ],
    )
    return VisionResult(
        primary_state=state,
        perception=None,
        raw_ai_output=reason,
        needs_manual_review=True,
        processing_latency_ms=latency_ms,
        model_version=model_version,
    )
