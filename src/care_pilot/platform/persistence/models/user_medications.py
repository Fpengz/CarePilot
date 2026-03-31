"""
Models for user-specific medication data, linking to regimens.
"""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship  # Import Relationship

from care_pilot.platform.persistence.models.base import BaseRecord, TimestampMixin

if TYPE_CHECKING:
    from care_pilot.platform.persistence.models.profiles import UserProfileRecord


class UserMedicationRecord(BaseRecord, TimestampMixin, table=True):
    """
    Represents a user's specific medication entry, linking to a regimen.
    """

    __tablename__ = "user_medications"

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, foreign_key="user_profiles.id")
    regimen_id: str | None = Field(
        index=True, foreign_key="medication_regimens.id"
    )  # Links to the canonical regimen
    medication_name: str  # Denormalized for quick access, should match regimen_id's name if regimen_id is present
    dosage_text: str  # Denormalized for quick access
    frequency_type: str  # Denormalized for quick access
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool = True
    # Add any user-specific overrides or notes here, e.g., "take with food"
    user_notes: str | None = None

    # Define the back_populates relationship
    user_profile: Mapped["UserProfileRecord"] = Relationship(back_populates="medications")
