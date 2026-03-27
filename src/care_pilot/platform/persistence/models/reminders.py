"""
Reminder persistence models.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship  # Import Relationship

from care_pilot.platform.persistence.models.base import BaseRecord, TimestampMixin
from care_pilot.platform.persistence.models.reminder_definition_channels import (
    ReminderDefinitionChannelRecord,
)
from care_pilot.platform.persistence.models.reminder_schedule_rules import (
    ReminderScheduleRuleRecord,
)


class ReminderDefinitionRecord(BaseRecord, TimestampMixin, table=True):
    """
    SQLModel implementation of a reminder definition (the template).
    """

    __tablename__ = "reminder_definitions"

    id: str = Field(primary_key=True)
    user_id: str = Field(index=True, foreign_key="user_profiles.id")
    regimen_id: str | None = Field(default=None, index=True, foreign_key="medication_regimens.id")

    reminder_type: str
    source: str
    title: str
    body: str | None = None

    medication_name: str
    dosage_text: str
    route: str | None = None
    instructions_text: str | None = None
    special_notes: str | None = None
    treatment_duration: str | None = None

    timezone: str = "Asia/Singapore"
    active: bool = True

    # Define ORM relationships
    channels: list[ReminderDefinitionChannelRecord] = Relationship(back_populates="reminder_definition")
    schedule_rules: list[ReminderScheduleRuleRecord] = Relationship(back_populates="reminder_definition")

    # user_profile relationship would be defined in profiles.py


class ReminderOccurrenceRecord(BaseRecord, TimestampMixin, table=True):
    """
    SQLModel implementation of a specific reminder trigger instance.
    """

    __tablename__ = "reminder_occurrences"

    id: str = Field(primary_key=True)
    reminder_definition_id: str = Field(index=True, foreign_key="reminder_definitions.id")
    user_id: str = Field(index=True, foreign_key="user_profiles.id")

    scheduled_for: datetime = Field(index=True)
    trigger_at: datetime = Field(index=True)
    status: str = Field(index=True) # e.g., "pending", "sent", "acknowledged", "taken", "skipped", "missed"

    action: str | None = None
    action_outcome: str | None = None
    acted_at: datetime | None = None

    grace_window_minutes: int = 0
    retry_count: int = 0
    last_delivery_status: str | None = None

    metadata_json: dict = Field(default_factory=dict, sa_column=Column(JSON))

    # Define back_populates relationships
    # The 'user_profile' relationship would be defined in profiles.py
    # For reminder_definition, it should back_populate 'schedule_rules' or similar field in ReminderDefinitionRecord
    # Let's assume ReminderDefinitionRecord has a field 'schedule_rules' for this.
    reminder_definition: ReminderDefinitionRecord = Relationship(back_populates="schedule_rules")
