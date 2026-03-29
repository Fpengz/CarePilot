"""
Models for user-specific disliked ingredients.
"""

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship  # Import Relationship

from care_pilot.platform.persistence.models.base import BaseRecord, TimestampMixin

if TYPE_CHECKING:
    from care_pilot.platform.persistence.models.profiles import UserProfileRecord


class UserDislikedIngredientRecord(BaseRecord, TimestampMixin, table=True):
    """
    Represents a user's disliked ingredient.
    """

    __tablename__ = "user_disliked_ingredients"

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, foreign_key="user_profiles.id")
    ingredient_name: str = Field(index=True)

    # Define the back_populates relationship
    user_profile: Mapped["UserProfileRecord"] = Relationship(back_populates="disliked_ingredients")
