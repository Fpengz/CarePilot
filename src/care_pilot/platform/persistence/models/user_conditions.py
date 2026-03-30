"""
Models for user-specific condition data.
"""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship  # Import Relationship

from care_pilot.platform.persistence.models.base import BaseRecord, TimestampMixin

if TYPE_CHECKING:
    from care_pilot.platform.persistence.models.profiles import UserProfileRecord


class UserConditionRecord(BaseRecord, TimestampMixin, table=True):
    """
    Represents a user's medical condition.
    """

    __tablename__ = "user_conditions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, foreign_key="user_profiles.id")
    condition_name: str = Field(index=True)
    diagnosis_date: date | None = None
    severity: str | None = None  # e.g., "mild", "moderate", "severe"
    notes: str | None = None
    is_active: bool = True

    # Define the back_populates relationship
    user_profile: Mapped["UserProfileRecord"] = Relationship(back_populates="conditions")
