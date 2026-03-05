from __future__ import annotations

from datetime import date, datetime, time, timedelta
from uuid import uuid4

from dietary_guardian.models.medication import ReminderEvent
from dietary_guardian.models.mobility import MobilityReminderSettings


def default_mobility_settings(user_id: str) -> MobilityReminderSettings:
    return MobilityReminderSettings(user_id=user_id)


def parse_hhmm(value: str) -> time:
    hour_text, minute_text = value.split(":", 1)
    return time(hour=int(hour_text), minute=int(minute_text))


def generate_mobility_reminders(
    *,
    user_id: str,
    target_date: date,
    settings: MobilityReminderSettings,
) -> list[ReminderEvent]:
    if not settings.enabled:
        return []

    current = datetime.combine(target_date, parse_hhmm(settings.active_start_time))
    end = datetime.combine(target_date, parse_hhmm(settings.active_end_time))
    reminders: list[ReminderEvent] = []
    while current <= end:
        reminders.append(
            ReminderEvent(
                id=str(uuid4()),
                user_id=user_id,
                reminder_type="mobility",
                title="Time to move",
                body="Stand up, stretch, or take a short walk.",
                scheduled_at=current,
                status="sent",
                meal_confirmation="unknown",
            )
        )
        current += timedelta(minutes=settings.interval_minutes)
    return reminders
