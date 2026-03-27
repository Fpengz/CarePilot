"""
Defines specific rules for reminder scheduling.
"""
from __future__ import annotations

from datetime import date, time  # Added time for specific_time

from sqlalchemy import JSON, Column
from sqlmodel import Field

from care_pilot.platform.persistence.models.base import BaseRecord


class ReminderScheduleRuleRecord(BaseRecord, table=True):
    __tablename__ = "reminder_schedule_rules"
    id: int | None = Field(default=None, primary_key=True)
    reminder_definition_id: str = Field(index=True, foreign_key="reminder_definitions.id")
    # Example: "daily", "weekly", "monthly", "every_x_days"
    frequency_type: str = Field(index=True)
    # Example: For weekly, ["Mon", "Wed", "Fri"]; for daily, None or "all"
    frequency_days: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    # Specific time of day, e.g., "08:00"
    specific_time: time | None = None
    # For recurring schedules like "every 3 days"
    interval_days: int | None = None
    # For specific date ranges or conditions
    start_date: date | None = None
    end_date: date | None = None
    # Metadata or specific rule parameters
    rule_params: dict = Field(default_factory=dict, sa_column=Column(JSON))
