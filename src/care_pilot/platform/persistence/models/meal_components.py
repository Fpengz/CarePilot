"""
Models for individual meal components and their nutritional breakdown.
"""

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship  # Import Relationship

from care_pilot.platform.persistence.models.base import BaseRecord, TimestampMixin

if TYPE_CHECKING:
    from care_pilot.platform.persistence.models.meals import MealRecordRecord


class MealComponentRecord(BaseRecord, TimestampMixin, table=True):
    """
    Represents a single component of a meal (e.g., 'Chicken Rice', 'Sambal').
    Stores estimated nutritional values for that component.
    """

    __tablename__ = "meal_components"

    id: int | None = Field(default=None, primary_key=True)
    meal_record_id: str = Field(index=True, foreign_key="meal_records.id")

    component_name: str = Field(index=True)
    original_serving_description: str | None = None # e.g., "small", "large", "1 bowl"

    # Estimated nutritional values for this component
    calories_kcal: float = 0.0
    protein_g: float = 0.0
    carbohydrates_g: float = 0.0
    fat_g: float = 0.0
    sugar_g: float = 0.0
    sodium_mg: float = 0.0
    fiber_g: float = 0.0

    # Define the back_populates relationship
    meal_record: Mapped["MealRecordRecord"] = Relationship(back_populates="meal_components")
