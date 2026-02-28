import asyncio
from datetime import datetime, timezone

from dietary_guardian.models.medication import ReminderEvent
from dietary_guardian.services.reminder_notification_service import materialize_reminder_notifications
from dietary_guardian.services.reminder_scheduler import run_reminder_scheduler_once
from dietary_guardian.services.repository import SQLiteRepository


def test_run_reminder_scheduler_once_dispatches_and_delivers_due_notifications(tmp_path) -> None:
    repo = SQLiteRepository(str(tmp_path / "scheduler.db"))
    event = ReminderEvent(
        id="rem_sched_001",
        user_id="user_001",
        medication_name="Amlodipine",
        scheduled_at=datetime.now(timezone.utc),
        dosage_text="5mg",
    )
    repo.save_reminder_event(event)
    materialize_reminder_notifications(repository=repo, reminder_event=event, reminder_type="medication")

    result = asyncio.run(run_reminder_scheduler_once(repository=repo))

    assert result.queued_count == 1
    assert result.delivery_attempts == 1
    schedule = repo.list_scheduled_notifications(reminder_id=event.id)[0]
    assert schedule.status == "delivered"
