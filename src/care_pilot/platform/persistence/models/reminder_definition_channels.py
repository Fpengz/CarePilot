"""
Links reminder definitions to specific notification channels.
"""
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship

from care_pilot.platform.persistence.models.base import BaseRecord

if TYPE_CHECKING:
    from care_pilot.platform.persistence.models.reminders import ReminderDefinitionRecord


class ReminderDefinitionChannelRecord(BaseRecord, table=True):
    __tablename__ = "reminder_definition_channels"
    id: int | None = Field(default=None, primary_key=True)
    reminder_definition_id: str = Field(index=True, foreign_key="reminder_definitions.id")
    channel: str = Field(index=True) # e.g., "in_app", "sms", "telegram"

    reminder_definition: Mapped["ReminderDefinitionRecord"] = Relationship(
        back_populates="channels"
    )
