from datetime import datetime, timezone

from dietary_guardian.domain.notifications.models import ReminderEvent
from dietary_guardian.infrastructure.persistence import SQLiteAppStore
from dietary_guardian.application.notifications.reminder_materialization import (
    dispatch_due_reminder_notifications,
    materialize_reminder_notifications,
)


def _event() -> ReminderEvent:
    return ReminderEvent(
        id="rem_001",
        user_id="user_001",
        medication_name="Metformin",
        scheduled_at=datetime(2026, 2, 28, 12, 0, tzinfo=timezone.utc),
        dosage_text="500mg",
    )


def test_materialize_reminder_notifications_uses_default_in_app_fallback(tmp_path) -> None:
    repo = SQLiteAppStore(str(tmp_path / "notifications.db"))

    repo.save_reminder_event(_event())
    created = materialize_reminder_notifications(repository=repo, reminder_event=_event(), reminder_type="medication")

    assert len(created) == 1
    assert created[0].channel == "in_app"
    assert created[0].offset_minutes == 0
    assert created[0].status == "pending"


def test_dispatch_due_reminder_notifications_is_idempotent_per_schedule(tmp_path) -> None:
    repo = SQLiteAppStore(str(tmp_path / "notifications.db"))
    event = _event()
    repo.save_reminder_event(event)
    schedules = materialize_reminder_notifications(repository=repo, reminder_event=event, reminder_type="medication")

    first = dispatch_due_reminder_notifications(repository=repo, now=event.scheduled_at)
    second = dispatch_due_reminder_notifications(repository=repo, now=event.scheduled_at)

    assert len(schedules) == 1
    assert len(first) == 1
    assert second == []
