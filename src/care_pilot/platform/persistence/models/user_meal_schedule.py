"""
User meal schedule persistence model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from care_pilot.platform.persistence.models.base import BaseRecord, TimestampMixin

if TYPE_CHECKING:
    from care_pilot.platform.persistence.models.profiles import UserProfileRecord


class UserMealScheduleRecord(BaseRecord, TimestampMixin, table=True):
    """
    SQLModel implementation of user meal schedules.
    """

    __tablename__ = "user_meal_schedules"

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, foreign_key="user_profiles.id")
    day_of_week: int = Field(index=True)  # 0-6 (Monday to Sunday)
    meal_type: str = Field(index=True)  # e.g., "breakfast", "lunch", "dinner", "snack"
    time: str  # e.g., "08:00"
    notes: str | None = None

    # Define ORM relationships
    user_profile: UserProfileRecord = Relationship(back_populates="meal_schedule")
