"""
User nutrition goals persistence model.
"""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship

from care_pilot.platform.persistence.models.base import BaseRecord, TimestampMixin

if TYPE_CHECKING:
    from care_pilot.platform.persistence.models.profiles import UserProfileRecord


class UserNutritionGoalRecord(BaseRecord, TimestampMixin, table=True):
    """
    SQLModel implementation of user nutrition goals.
    """

    __tablename__ = "user_nutrition_goals"

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, foreign_key="user_profiles.id")
    goal_type: str = Field(index=True)  # e.g., "calories", "sodium", "sugar", "protein", "fiber"
    target_value: float
    unit: str
    start_date: date = Field(index=True)
    end_date: date | None = Field(default=None, index=True)

    # Define ORM relationships
    user_profile: Mapped["UserProfileRecord"] = Relationship(back_populates="nutrition_goals")
