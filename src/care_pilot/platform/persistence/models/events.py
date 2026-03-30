"""
System events and outbound alert models.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field

from care_pilot.platform.persistence.models.base import BaseRecord, TimestampMixin


class AlertOutboxRecord(BaseRecord, TimestampMixin, table=True):
    """
    SQLModel implementation of the alert outbox.
    Ensures reliable delivery of notifications.
    """

    __tablename__ = "alert_outbox"

    alert_id: str = Field(primary_key=True)
    sink: str = Field(primary_key=True)  # e.g., "telegram", "email"

    type: str = Field(index=True)
    severity: str = Field(index=True)
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))

    correlation_id: str = Field(index=True)
    state: str = Field(index=True)  # e.g., "queued", "sent", "failed"

    attempt_count: int = 0
    next_attempt_at: datetime = Field(index=True)
    last_error: str | None = None

    lease_owner: str | None = None
    lease_until: datetime | None = None
    idempotency_key: str = Field(index=True)


# ReminderEventRecord is deprecated and will be removed in a future migration.
# Its functionality is absorbed by ReminderOccurrenceRecord and MedicationAdherenceRecord.
class ReminderEventRecord(BaseRecord, TimestampMixin, table=True):
    """
    SQLModel implementation of a reminder event.
    Historically used for flat event logs, still referenced by adherence.
    """

    __tablename__ = "reminder_events"

    id: str = Field(primary_key=True)
    user_id: str = Field(index=True, foreign_key="user_profiles.id")
    reminder_definition_id: str | None = Field(default=None, index=True, foreign_key="reminder_definitions.id")
    occurrence_id: str | None = Field(default=None, index=True, foreign_key="reminder_occurrences.id")
    regimen_id: str | None = Field(default=None, index=True, foreign_key="medication_regimens.id")

    reminder_type: str = "medication"
    title: str = "Medication Reminder"
    body: str | None = None
    medication_name: str
    scheduled_at: datetime = Field(index=True)
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    acknowledged_at: datetime | None = None
