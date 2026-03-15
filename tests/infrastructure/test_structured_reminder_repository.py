"""Tests for structured reminder persistence."""

from __future__ import annotations

from datetime import date, datetime, timezone

from care_pilot.features.reminders.domain.models import (
    ReminderActionRecord,
    ReminderDefinition,
    ReminderOccurrence,
    ReminderScheduleRule,
)
from care_pilot.platform.persistence import SQLiteAppStore


def test_structured_reminder_repository_round_trip(tmp_path) -> None:
    repo = SQLiteAppStore(str(tmp_path / "structured-reminders.db"))
    definition = ReminderDefinition(
        id="def_001",
        user_id="user_001",
        title="Take Metformin 500mg",
        reminder_type="medication",
        source="manual",
        channels=["in_app", "chat"],
        schedule=ReminderScheduleRule(
            pattern="daily_fixed_times",
            times=["08:00", "20:00"],
            timezone="Asia/Singapore",
            start_date=date(2026, 3, 14),
        ),
        medication_name="Metformin",
        dosage_text="500mg",
        instructions_text="Twice daily after meals",
    )

    saved_definition = repo.save_reminder_definition(definition)
    fetched_definition = repo.get_reminder_definition(definition.id)

    assert saved_definition.id == definition.id
    assert fetched_definition is not None
    assert fetched_definition.title == "Take Metformin 500mg"
    assert fetched_definition.schedule.pattern == "daily_fixed_times"
    assert fetched_definition.channels == ["in_app", "chat"]

    occurrence = ReminderOccurrence(
        id="occ_001",
        reminder_definition_id=definition.id,
        user_id="user_001",
        scheduled_for=datetime(2026, 3, 14, 8, 0, tzinfo=timezone.utc),
        trigger_at=datetime(2026, 3, 14, 8, 0, tzinfo=timezone.utc),
        status="scheduled",
    )
    saved_occurrence = repo.save_reminder_occurrence(occurrence)

    assert saved_occurrence.id == occurrence.id
    upcoming = repo.list_reminder_occurrences(user_id="user_001", status="scheduled")
    assert [item.id for item in upcoming] == ["occ_001"]

    action = ReminderActionRecord(
        id="act_001",
        occurrence_id="occ_001",
        reminder_definition_id="def_001",
        user_id="user_001",
        action="taken",
        acted_at=datetime(2026, 3, 14, 8, 5, tzinfo=timezone.utc),
    )
    repo.append_reminder_action(action)
    repo.update_reminder_occurrence_status(
        occurrence_id="occ_001",
        status="completed",
        acted_at=action.acted_at,
        action="taken",
    )

    history = repo.list_reminder_occurrences(user_id="user_001", status="completed")
    assert [item.id for item in history] == ["occ_001"]
    assert history[0].action == "taken"
    actions = repo.list_reminder_actions(occurrence_id="occ_001")
    assert len(actions) == 1
    assert actions[0].action == "taken"
