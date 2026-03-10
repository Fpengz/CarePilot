"""Domain models for daily nutrition summaries."""

from pydantic import BaseModel, Field


class NutritionTotals(BaseModel):
    calories: float = 0.0
    sugar_g: float = 0.0
    sodium_mg: float = 0.0
    protein_g: float = 0.0
    fiber_g: float = 0.0


class NutritionInsight(BaseModel):
    code: str
    title: str
    summary: str
    actions: list[str] = Field(default_factory=list)


class DailyNutritionSummary(BaseModel):
    date: str
    meal_count: int
    last_logged_at: str | None = None
    consumed: NutritionTotals
    targets: NutritionTotals
    remaining: NutritionTotals
    insights: list[NutritionInsight] = Field(default_factory=list)
    recommendation_hints: list[str] = Field(default_factory=list)
