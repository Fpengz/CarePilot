"""Feature models for the meal analysis pipeline (stages 1–4)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from dietary_guardian.features.meals.domain import NormalizedMealItem, VisionResult


class DietaryClaim(BaseModel):
    label: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class DietaryClaims(BaseModel):
    claimed_items: list[DietaryClaim] = Field(default_factory=list)
    consumption_fraction: float = Field(default=1.0, ge=0.0, le=1.0)
    meal_time_label: str | None = None
    vendor_or_source: str | None = None
    preparation_override: str | None = None
    dietary_constraints: list[str] = Field(default_factory=list)
    goal_context: str | None = None
    certainty_level: str | None = None
    ambiguity_notes: list[str] = Field(default_factory=list)


class ContextSnapshot(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meal_window: str | None = None
    location_cluster: str | None = None
    vendor_candidates: list[str] = Field(default_factory=list)
    regional_food_prior: list[str] = Field(default_factory=list)
    user_context_snapshot: dict[str, object] = Field(default_factory=dict)


class RawObservationBundle(BaseModel):
    observation_id: str = Field(default_factory=lambda: uuid4().hex)
    user_id: str
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: Literal["upload", "camera", "unknown"] = "unknown"
    vision_result: VisionResult
    dietary_claims: DietaryClaims
    context: ContextSnapshot
    image_quality: str | None = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    unresolved_conflicts: list[str] = Field(default_factory=list)


class ValidatedMealEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: uuid4().hex)
    user_id: str
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meal_name: str
    consumption_fraction: float = Field(default=1.0, ge=0.0, le=1.0)
    canonical_items: list[NormalizedMealItem] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    confidence_summary: dict[str, object] = Field(default_factory=dict)
    provenance: dict[str, object] = Field(default_factory=dict)
    needs_manual_review: bool = False


class NutritionRiskProfile(BaseModel):
    profile_id: str = Field(default_factory=lambda: uuid4().hex)
    event_id: str
    user_id: str
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    calories: float = Field(default=0.0, ge=0.0)
    carbs_g: float = Field(default=0.0, ge=0.0)
    sugar_g: float = Field(default=0.0, ge=0.0)
    protein_g: float = Field(default=0.0, ge=0.0)
    fat_g: float = Field(default=0.0, ge=0.0)
    sodium_mg: float = Field(default=0.0, ge=0.0)
    fiber_g: float = Field(default=0.0, ge=0.0)
    risk_tags: list[str] = Field(default_factory=list)
    uncertainty: dict[str, object] = Field(default_factory=dict)


class MealAnalysisResult(BaseModel):
    raw_observation: RawObservationBundle
    validated_event: ValidatedMealEvent
    nutrition_profile: NutritionRiskProfile
