"""
Links reminder definitions to specific notification channels.
"""
from __future__ import annotations

from sqlmodel import Field

from care_pilot.platform.persistence.models.base import BaseRecord


class ReminderDefinitionChannelRecord(BaseRecord, table=True):
    __tablename__ = "reminder_definition_channels"
    id: int | None = Field(default=None, primary_key=True)
    reminder_definition_id: str = Field(index=True, foreign_key="reminder_definitions.id")
    channel: str = Field(index=True) # e.g., "in_app", "sms", "telegram"
