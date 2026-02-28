from typing import Literal

from pydantic import BaseModel, Field

from dietary_guardian.models.user import MedicalCondition, Medication

BudgetTier = Literal["budget", "moderate", "flexible"]
CompletenessState = Literal["needs_profile", "partial", "ready"]


class ProfileCompleteness(BaseModel):
    state: CompletenessState
    missing_fields: list[str] = Field(default_factory=list)


class HealthProfileRecord(BaseModel):
    user_id: str
    age: int | None = None
    locale: str = "en-SG"
    height_cm: float | None = None
    weight_kg: float | None = None
    daily_sodium_limit_mg: float = 2000.0
    daily_sugar_limit_g: float = 30.0
    target_calories_per_day: float | None = None
    macro_focus: list[str] = Field(default_factory=list)
    conditions: list[MedicalCondition] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    nutrition_goals: list[str] = Field(default_factory=list)
    preferred_cuisines: list[str] = Field(default_factory=list)
    disliked_ingredients: list[str] = Field(default_factory=list)
    budget_tier: BudgetTier = "moderate"
    updated_at: str | None = None
