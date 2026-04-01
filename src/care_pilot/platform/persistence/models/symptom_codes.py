"""
Models for individual symptom codes linked to a check-in.
"""

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship  # Import Relationship

from care_pilot.platform.persistence.models.base import BaseRecord, TimestampMixin

if TYPE_CHECKING:
    from care_pilot.platform.persistence.models.clinical import SymptomCheckInRecord


class SymptomCodeRecord(BaseRecord, TimestampMixin, table=True):
    """
    Represents a specific symptom code linked to a SymptomCheckInRecord.
    """

    __tablename__ = "symptom_codes"

    id: int | None = Field(default=None, primary_key=True)
    symptom_checkin_id: str = Field(index=True, foreign_key="symptom_checkins.id")
    code: str = Field(index=True)  # The actual symptom code string
    # Optional: Add confidence score or agent details if needed
    # agent_details: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    # Define the back_populates relationship
    symptom_checkin: Mapped["SymptomCheckInRecord"] = Relationship(back_populates="symptom_codes")
