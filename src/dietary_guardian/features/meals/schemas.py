"""
Define meal feature schemas.

This module contains Pydantic schemas shared between meal domain and API
layers.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DailyNutritionTotalsResponse(BaseModel):
    calories: float
    sugar_g: float
    sodium_mg: float
    protein_g: float
    fiber_g: float


class DailyNutritionInsightResponse(BaseModel):
    code: str
    title: str
    summary: str
    actions: list[str] = Field(default_factory=list)


class MealDailySummaryResponse(BaseModel):
    date: str
    meal_count: int
    last_logged_at: datetime | None = None
    consumed: DailyNutritionTotalsResponse
    targets: DailyNutritionTotalsResponse
    remaining: DailyNutritionTotalsResponse
    insights: list[DailyNutritionInsightResponse] = Field(default_factory=list)
    recommendation_hints: list[str] = Field(default_factory=list)
