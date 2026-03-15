"""Deterministic reminder definition and occurrence generation."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from dietary_guardian.features.profiles.domain.models import MealSlot, UserProfile
from dietary_guardian.features.reminders.domain.models import (
    MedicationRegimen,
    ReminderDefinition,
    ReminderOccurrence,
    ReminderScheduleRule,
)

DEFAULT_ANCHORS: dict[str, str] = {
    "breakfast": "08:00",
    "lunch": "13:00",
    "dinner": "19:00",
    "bedtime": "22:00",
}


def _parse_hhmm(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(hour=int(hour), minute=int(minute))


def _combine_local(*, target_date: date, value: str, timezone_name: str) -> datetime:
    local = datetime.combine(target_date, _parse_hhmm(value))
    return local.replace(tzinfo=ZoneInfo(timezone_name)).astimezone(ZoneInfo("UTC"))


def schedule_rule_from_regimen(regimen: MedicationRegimen) -> ReminderScheduleRule:
    if regimen.timing_type == "fixed_time":
        return ReminderScheduleRule(
            pattern="daily_fixed_times",
            times=[regimen.fixed_time] if regimen.fixed_time else [],
            timezone=regimen.timezone,
            start_date=regimen.start_date,
            end_date=regimen.end_date,
            metadata={"frequency_type": regimen.frequency_type},
        )

    primary_slot: MealSlot | None = regimen.slot_scope[0] if regimen.slot_scope else None
    direction = "before" if regimen.timing_type == "pre_meal" else "after"
    return ReminderScheduleRule(
        pattern="meal_relative",
        meal_slot=primary_slot,
        relative_direction=direction,
        offset_minutes=regimen.offset_minutes,
        timezone=regimen.timezone,
        start_date=regimen.start_date,
        end_date=regimen.end_date,
        metadata={
            "slot_scope": list(regimen.slot_scope),
            "frequency_type": regimen.frequency_type,
            "frequency_times_per_day": regimen.frequency_times_per_day,
        },
    )


def definition_from_regimen(regimen: MedicationRegimen) -> ReminderDefinition:
    summary = regimen.instructions_text or f"{regimen.medication_name} {regimen.dosage_text}".strip()
    return ReminderDefinition(
        id=str(uuid4()),
        user_id=regimen.user_id,
        regimen_id=regimen.id,
        reminder_type="medication",
        source="manual" if regimen.source_type == "manual" else regimen.source_type,
        title=f"Take {regimen.medication_name}".strip(),
        body=summary,
        medication_name=regimen.medication_name,
        dosage_text=regimen.dosage_text,
        instructions_text=regimen.instructions_text,
        treatment_duration=_treatment_duration(regimen),
        channels=["in_app"],
        timezone=regimen.timezone,
        schedule=schedule_rule_from_regimen(regimen),
        active=regimen.active,
    )


def _treatment_duration(regimen: MedicationRegimen) -> str | None:
    if regimen.start_date and regimen.end_date:
        return f"{regimen.start_date.isoformat()} to {regimen.end_date.isoformat()}"
    if regimen.start_date:
        return f"starting {regimen.start_date.isoformat()}"
    if regimen.end_date:
        return f"until {regimen.end_date.isoformat()}"
    return None


def occurrences_for_definition(
    *,
    definition: ReminderDefinition,
    target_date: date,
    user_profile: UserProfile,
) -> list[ReminderOccurrence]:
    if not definition.active:
        return []
    if definition.schedule.start_date and target_date < definition.schedule.start_date:
        return []
    if definition.schedule.end_date and target_date > definition.schedule.end_date:
        return []

    timezone_name = definition.schedule.timezone or definition.timezone
    trigger_times: list[datetime] = []
    if definition.schedule.pattern == "daily_fixed_times":
        for item in definition.schedule.times:
            trigger_times.append(_combine_local(target_date=target_date, value=item, timezone_name=timezone_name))
    elif definition.schedule.pattern == "one_time":
        if definition.schedule.start_date and definition.schedule.start_date != target_date:
            return []
        for item in definition.schedule.times:
            trigger_times.append(_combine_local(target_date=target_date, value=item, timezone_name=timezone_name))
    elif definition.schedule.pattern == "specific_weekdays":
        if not definition.schedule.weekdays:
            return []
        if (target_date.weekday() + 1) not in definition.schedule.weekdays:
            return []
        for item in definition.schedule.times:
            trigger_times.append(_combine_local(target_date=target_date, value=item, timezone_name=timezone_name))
    elif definition.schedule.pattern == "every_x_hours":
        interval = definition.schedule.interval_hours or 0
        if interval <= 0:
            return []
        anchor = definition.schedule.times[0] if definition.schedule.times else "08:00"
        cursor = _combine_local(target_date=target_date, value=anchor, timezone_name=timezone_name)
        end_of_day = _combine_local(
            target_date=target_date + timedelta(days=1),
            value="00:00",
            timezone_name=timezone_name,
        )
        while cursor < end_of_day:
            trigger_times.append(cursor)
            cursor += timedelta(hours=interval)
    elif definition.schedule.pattern == "meal_relative":
        raw_scope = definition.schedule.metadata.get("slot_scope")
        slot_scope = list(raw_scope) if isinstance(raw_scope, list) and raw_scope else (
            [definition.schedule.meal_slot] if definition.schedule.meal_slot else []
        )
        for slot in slot_scope:
            meal_window = next((item for item in user_profile.meal_schedule if item.slot == slot), None)
            anchor = DEFAULT_ANCHORS.get(str(slot), "08:00")
            if meal_window is not None:
                anchor = meal_window.start_time if definition.schedule.relative_direction == "before" else meal_window.end_time
            resolved = _combine_local(target_date=target_date, value=anchor, timezone_name=timezone_name)
            offset = timedelta(minutes=definition.schedule.offset_minutes)
            trigger_times.append(resolved - offset if definition.schedule.relative_direction == "before" else resolved + offset)
    else:
        return []

    return [
        ReminderOccurrence(
            id=str(uuid4()),
            reminder_definition_id=definition.id,
            user_id=definition.user_id,
            scheduled_for=trigger_at,
            trigger_at=trigger_at,
            status="scheduled",
            metadata={
                "medication_name": definition.medication_name,
                "dosage_text": definition.dosage_text,
                "title": definition.title,
                "body": definition.body,
            },
        )
        for trigger_at in sorted(trigger_times)
    ]
