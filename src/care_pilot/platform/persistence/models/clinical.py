"""
Clinical data persistence models (Biomarkers and Symptoms).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship  # Import Relationship

from care_pilot.platform.persistence.models.base import BaseRecord, TimestampMixin
from care_pilot.platform.persistence.models.symptom_codes import (
    SymptomCodeRecord,  # Import new model
)

if TYPE_CHECKING:
    from care_pilot.platform.persistence.models.profiles import UserProfileRecord


class BiomarkerReadingRecord(BaseRecord, TimestampMixin, table=True):
    """
    SQLModel implementation of a biomarker reading.
    """

    __tablename__ = "biomarker_readings"

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, foreign_key="user_profiles.id")
    name: str = Field(index=True)  # e.g., "glucose", "systolic_bp"
    value: float
    unit: str | None = None
    reference_range: str | None = None
    measured_at: datetime = Field(index=True)
    source_doc_id: str | None = None

    # Define ORM relationships
    user_profile: UserProfileRecord = Relationship(back_populates="biomarker_readings")
 # Assuming UserProfileRecord has 'biomarker_readings' field


class SymptomCheckInRecord(BaseRecord, TimestampMixin, table=True):
    """
    SQLModel implementation of a symptom check-in.
    """

    __tablename__ = "symptom_checkins"

    id: str = Field(primary_key=True)
    user_id: str = Field(index=True, foreign_key="user_profiles.id")
    recorded_at: datetime = Field(index=True)
    severity: int = Field(index=True)  # 1-10

    free_text: str | None = None
    context: dict = Field(default_factory=dict, sa_column=Column(JSON))
    safety: dict = Field(default_factory=dict, sa_column=Column(JSON))

    # Define ORM relationships
    symptom_codes: list[SymptomCodeRecord] = Relationship(back_populates="symptom_checkin")
    user_profile: UserProfileRecord = Relationship(back_populates="symptom_checkins")
 # Assuming UserProfileRecord has 'symptom_checkins' field
