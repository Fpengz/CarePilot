"""
Define health profile schemas.

This module contains Pydantic schemas shared between profile domain and API
layers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from care_pilot.features.profiles.domain.models import MealScheduleWindow


class HealthProfileCondition(BaseModel):
    name: str
    severity: str


class HealthProfileMedication(BaseModel):
    name: str
    dosage: str
    contraindications: list[str] = Field(default_factory=list)


class HealthProfileCompletenessResponse(BaseModel):
    state: Literal["needs_profile", "partial", "ready"]
    missing_fields: list[str] = Field(default_factory=list)


class HealthProfileResponseItem(BaseModel):
    age: int | None = None
    locale: str
    height_cm: float | None = None
    weight_kg: float | None = None
    bmi: float | None = None
    daily_sodium_limit_mg: float
    daily_sugar_limit_g: float
    daily_protein_target_g: float
    daily_fiber_target_g: float
    target_calories_per_day: float | None = None
    macro_focus: list[str] = Field(default_factory=list)
    conditions: list[HealthProfileCondition] = Field(default_factory=list)
    medications: list[HealthProfileMedication] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    nutrition_goals: list[str] = Field(default_factory=list)
    preferred_cuisines: list[str] = Field(default_factory=list)
    disliked_ingredients: list[str] = Field(default_factory=list)
    budget_tier: Literal["budget", "moderate", "flexible"] = "moderate"
    meal_schedule: list[MealScheduleWindow] = Field(default_factory=list)
    preferred_notification_channel: str = "in_app"
    fallback_mode: bool = False
    completeness: HealthProfileCompletenessResponse
    updated_at: datetime | None = None
