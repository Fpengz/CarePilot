"""
UserProfile persistence models.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship  # Import Relationship

from care_pilot.platform.persistence.models.base import BaseRecord, TimestampMixin
from care_pilot.platform.persistence.models.clinical import (
    BiomarkerReadingRecord,
    SymptomCheckInRecord,
)

# Assuming MealRecordRecord, BiomarkerReadingRecord, SymptomCheckInRecord are importable
from care_pilot.platform.persistence.models.meals import MealRecordRecord
from care_pilot.platform.persistence.models.user_conditions import UserConditionRecord
from care_pilot.platform.persistence.models.user_disliked_ingredients import (
    UserDislikedIngredientRecord,
)
from care_pilot.platform.persistence.models.user_medications import UserMedicationRecord

if TYPE_CHECKING:
    from care_pilot.platform.persistence.models.user_meal_schedule import UserMealScheduleRecord
    from care_pilot.platform.persistence.models.user_nutrition_goals import UserNutritionGoalRecord


class UserProfileRecord(BaseRecord, TimestampMixin, table=True):
    """
    SQLModel implementation of the user profile.
    This consolidates demographics, medical conditions, and preferences.
    """

    __tablename__ = "user_profiles"

    id: str = Field(primary_key=True)
    name: str = Field(index=True)
    age: int
    profile_mode: str = "self"
    locale: str = "en-SG"

    # Allergies remain as a JSON list for now.
    allergies: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    budget_tier: str = "moderate"
    target_calories_per_day: float | None = None

    # Targets & Limits
    daily_sodium_limit_mg: float = 2000.0
    daily_sugar_limit_g: float = 30.0
    daily_protein_target_g: float = 60.0
    daily_fiber_target_g: float = 25.0

    # Define ORM relationships (back_populates side)
    conditions: list[UserConditionRecord] = Relationship(back_populates="user_profile")
    medications: list[UserMedicationRecord] = Relationship(back_populates="user_profile")
    disliked_ingredients: list[UserDislikedIngredientRecord] = Relationship(back_populates="user_profile")

    # Relationships to clinical records
    meal_records: list[MealRecordRecord] = Relationship(back_populates="user_profile")
    biomarker_readings: list[BiomarkerReadingRecord] = Relationship(back_populates="user_profile")
    symptom_checkins: list[SymptomCheckInRecord] = Relationship(back_populates="user_profile")

    # New relationships for normalized goals and schedules
    nutrition_goals: list[UserNutritionGoalRecord] = Relationship(back_populates="user_profile")
    meal_schedule: list[UserMealScheduleRecord] = Relationship(back_populates="user_profile")
