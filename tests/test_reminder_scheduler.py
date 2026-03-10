import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from dietary_guardian.domain.notifications.models import ReminderEvent
from dietary_guardian.infrastructure.persistence import SQLiteAppStore
from dietary_guardian.runtime.schedulers import reminder_scheduler
from dietary_guardian.application.notifications.reminder_materialization import (
    materialize_reminder_notifications,
)
from dietary_guardian.runtime.schedulers.reminder_scheduler import run_reminder_scheduler_once


def test_run_reminder_scheduler_once_dispatches_and_delivers_due_notifications(tmp_path) -> None:
    repo = SQLiteAppStore(str(tmp_path / "scheduler.db"))
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


def test_run_reminder_scheduler_once_builds_configured_store_when_repository_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_repo = object()
    settings = SimpleNamespace(
        workers=SimpleNamespace(
            reminder_scheduler_batch_size=25,
            alert_worker_max_attempts=3,
            alert_worker_concurrency=4,
        )
    )
    recorded: dict[str, object] = {}

    def fake_get_settings() -> SimpleNamespace:
        return settings

    def fake_build_reminder_scheduler_repository(passed_settings: object) -> object:
        recorded["settings"] = passed_settings
        return fake_repo

    def fake_dispatch_due_reminder_notifications(*, repository: object, now: datetime, limit: int) -> list[object]:
        recorded["dispatch_repository"] = repository
        recorded["dispatch_limit"] = limit
        return []

    monkeypatch.setattr(reminder_scheduler, "get_settings", fake_get_settings)
    monkeypatch.setattr(
        reminder_scheduler,
        "build_reminder_scheduler_repository",
        fake_build_reminder_scheduler_repository,
    )
    monkeypatch.setattr(reminder_scheduler, "dispatch_due_reminder_notifications", fake_dispatch_due_reminder_notifications)

    result = asyncio.run(run_reminder_scheduler_once())

    assert result == reminder_scheduler.ReminderSchedulerRunResult(queued_count=0, delivery_attempts=0)
    assert recorded["settings"] is settings
    assert recorded["dispatch_repository"] is fake_repo
    assert recorded["dispatch_limit"] == settings.workers.reminder_scheduler_batch_size
