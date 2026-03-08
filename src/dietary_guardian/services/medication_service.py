from datetime import date, datetime, time, timedelta, timezone
from typing import Protocol
from uuid import uuid4

from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.analytics import EngagementMetrics
from dietary_guardian.models.medication import MedicationRegimen, ReminderEvent
from dietary_guardian.models.user import MealScheduleWindow, UserProfile

logger = get_logger(__name__)

ASIA_SINGAPORE = "+08:00"


class ReminderEventRepository(Protocol):
    def get_reminder_event(self, event_id: str) -> ReminderEvent | None: ...

    def save_reminder_event(self, event: ReminderEvent) -> None: ...


def _parse_hhmm(value: str) -> time:
    hh, mm = value.split(":", 1)
    return time(hour=int(hh), minute=int(mm))


def _at(d: date, hhmm: str) -> datetime:
    t = _parse_hhmm(hhmm)
    return datetime.combine(d, t)


def _find_slot_window(user: UserProfile, slot: str) -> MealScheduleWindow | None:
    for window in user.meal_schedule:
        if window.slot == slot:
            return window
    return None


def generate_daily_reminders(
    user: UserProfile,
    regimens: list[MedicationRegimen],
    target_date: date,
) -> list[ReminderEvent]:
    logger.info(
        "generate_daily_reminders_start user_id=%s regimens=%s target_date=%s",
        user.id,
        len(regimens),
        target_date.isoformat(),
    )
    reminders: list[ReminderEvent] = []
    for regimen in regimens:
        if not regimen.active:
            continue

        if regimen.timing_type == "fixed_time":
            if not regimen.fixed_time:
                logger.warning(
                    "regimen_skipped_missing_fixed_time regimen_id=%s user_id=%s",
                    regimen.id,
                    user.id,
                )
                continue
            reminders.append(
                ReminderEvent(
                    id=str(uuid4()),
                    user_id=user.id,
                    reminder_type="medication",
                    title="Medication Reminder",
                    body=f"{regimen.medication_name} {regimen.dosage_text}".strip(),
                    medication_name=regimen.medication_name,
                    scheduled_at=_at(target_date, regimen.fixed_time),
                    slot=None,
                    dosage_text=regimen.dosage_text,
                    status="sent",
                    meal_confirmation="unknown",
                )
            )
            continue

        for slot in regimen.slot_scope:
            window = _find_slot_window(user, slot)
            if window is None:
                logger.warning(
                    "regimen_slot_missing_window regimen_id=%s slot=%s user_id=%s",
                    regimen.id,
                    slot,
                    user.id,
                )
                continue
            if regimen.timing_type == "pre_meal":
                scheduled = _at(target_date, window.start_time) - timedelta(minutes=regimen.offset_minutes)
            else:  # post_meal
                scheduled = _at(target_date, window.end_time) + timedelta(minutes=regimen.offset_minutes)
            reminders.append(
                ReminderEvent(
                    id=str(uuid4()),
                    user_id=user.id,
                    reminder_type="medication",
                    title="Medication Reminder",
                    body=f"{regimen.medication_name} {regimen.dosage_text}".strip(),
                    medication_name=regimen.medication_name,
                    scheduled_at=scheduled,
                    slot=slot,
                    dosage_text=regimen.dosage_text,
                    status="sent",
                    meal_confirmation="unknown",
                )
            )
    result = sorted(reminders, key=lambda item: item.scheduled_at)
    logger.info(
        "generate_daily_reminders_complete user_id=%s reminders=%s",
        user.id,
        len(result),
    )
    return result


def mark_meal_confirmation(
    event_id: str,
    confirmed: bool,
    confirmed_at: datetime | None,
    repository: ReminderEventRepository,
) -> ReminderEvent:
    logger.info("mark_meal_confirmation_start event_id=%s confirmed=%s", event_id, confirmed)
    event = repository.get_reminder_event(event_id)
    if event is None:
        logger.error("mark_meal_confirmation_missing_event event_id=%s", event_id)
        raise KeyError(f"Reminder event not found: {event_id}")

    if confirmed:
        event.meal_confirmation = "yes"
        event.status = "acknowledged"
        event.ack_at = confirmed_at or datetime.now(timezone.utc)
    else:
        event.meal_confirmation = "no"
        event.status = "missed"
        event.ack_at = confirmed_at or datetime.now(timezone.utc)

    repository.save_reminder_event(event)
    logger.info(
        "mark_meal_confirmation_complete event_id=%s status=%s meal_confirmation=%s",
        event.id,
        event.status,
        event.meal_confirmation,
    )
    return event


def compute_mcr(events: list[ReminderEvent]) -> EngagementMetrics:
    reminders_sent = len(events)
    yes_count = sum(1 for e in events if e.meal_confirmation == "yes")
    no_count = sum(1 for e in events if e.meal_confirmation == "no")
    rate = (yes_count / reminders_sent) if reminders_sent else 0.0
    metrics = EngagementMetrics(
        reminders_sent=reminders_sent,
        meal_confirmed_yes=yes_count,
        meal_confirmed_no=no_count,
        meal_confirmation_rate=rate,
    )
    logger.debug(
        "compute_mcr reminders_sent=%s yes=%s no=%s rate=%.4f",
        reminders_sent,
        yes_count,
        no_count,
        rate,
    )
    return metrics
