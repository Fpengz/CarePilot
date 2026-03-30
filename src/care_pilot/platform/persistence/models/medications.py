"""
Medication persistence models.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field

from care_pilot.platform.persistence.models.base import BaseRecord, TimestampMixin


class MedicationRegimenRecord(BaseRecord, TimestampMixin, table=True):
    """
    SQLModel implementation of a medication regimen.
    Root of the medication/reminder hierarchy.
    """

    __tablename__ = "medication_regimens"

    id: str = Field(primary_key=True)
    user_id: str = Field(index=True, foreign_key="user_profiles.id")
    medication_name: str = Field(index=True)
    canonical_name: str | None = None
    dosage_text: str
    timing_type: str  # e.g., "fixed", "event_driven"
    frequency_type: str = "fixed_time"
    frequency_times_per_day: int = 1

    time_rules: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    slot_scope: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    offset_minutes: int = 0
    fixed_time: str | None = None
    max_daily_doses: int = 1
    instructions_text: str | None = None

    source_type: str = "manual"
    source_filename: str | None = None
    source_hash: str | None = None

    start_date: date | None = None
    end_date: date | None = None
    timezone: str = "Asia/Singapore"
    parse_confidence: float | None = None
    active: bool = True


class MedicationAdherenceRecord(BaseRecord, TimestampMixin, table=True):
    """
    SQLModel implementation of a medication adherence event.
    Logs whether a medication was taken.
    """

    __tablename__ = "medication_adherence_events"

    id: str = Field(primary_key=True)
    user_id: str = Field(index=True, foreign_key="user_profiles.id")
    regimen_id: str = Field(index=True, foreign_key="medication_regimens.id")
    # Removed: reminder_id: Optional[str] = Field(default=None, index=True, foreign_key="reminder_events.id")
    occurrence_id: str = Field(index=True, foreign_key="reminder_occurrences.id") # Links to the specific reminder occurrence

    status: str = Field(index=True)  # e.g., "taken", "skipped", "missed"
    scheduled_at: datetime = Field(index=True)
    taken_at: datetime | None = None

    source: str = "manual"
    metadata_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
