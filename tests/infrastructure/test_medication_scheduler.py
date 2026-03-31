"""Tests for medication scheduler."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from care_pilot.features.medications.domain import generate_daily_reminders, mark_meal_confirmation
from care_pilot.features.profiles.domain.models import MedicalCondition, Medication, UserProfile
from care_pilot.features.reminders.domain.models import MedicationRegimen, ReminderEvent
from care_pilot.platform.persistence import SQLiteRepository

SGT = ZoneInfo("Asia/Singapore")


def _user() -> UserProfile:
    return UserProfile(
        id="u1",
        name="Mr Tan",
        age=68,
        conditions=[MedicalCondition(name="Hypertension", severity="High")],
        medications=[Medication(name="Amlodipine", dosage="5mg")],
    )


def test_generate_pre_post_fixed_reminders() -> None:
    user = _user()
    regimens = [
        MedicationRegimen(
            id="r1",
            user_id="u1",
            medication_name="Amlodipine",
            dosage_text="5mg",
            timing_type="pre_meal",
            offset_minutes=30,
            slot_scope=["lunch"],
            timezone="Asia/Singapore",
        ),
        MedicationRegimen(
            id="r2",
            user_id="u1",
            medication_name="Metformin",
            dosage_text="500mg",
            timing_type="post_meal",
            offset_minutes=30,
            slot_scope=["dinner"],
            timezone="Asia/Singapore",
        ),
        MedicationRegimen(
            id="r3",
            user_id="u1",
            medication_name="Statin",
            dosage_text="10mg",
            timing_type="fixed_time",
            fixed_time="22:00",
            timezone="Asia/Singapore",
        ),
    ]

    reminders = generate_daily_reminders(user, regimens, date(2026, 2, 24))

    assert len(reminders) == 3
    # 11:30 SGT is 03:30 UTC
    assert reminders[0].scheduled_at == datetime(2026, 2, 24, 11, 30, tzinfo=SGT).astimezone(UTC)
    # 20:30 SGT is 12:30 UTC
    assert reminders[1].scheduled_at == datetime(2026, 2, 24, 20, 30, tzinfo=SGT).astimezone(UTC)
    # 22:00 SGT is 14:00 UTC
    assert reminders[2].scheduled_at == datetime(2026, 2, 24, 22, 0, tzinfo=SGT).astimezone(UTC)


def test_mark_meal_confirmation_updates_status(tmp_path) -> None:
    repo = SQLiteRepository(str(tmp_path / "med.db"))
    event = ReminderEvent(
        id="e1",
        user_id="u1",
        medication_name="Amlodipine",
        scheduled_at=datetime(2026, 2, 24, 11, 30, tzinfo=UTC),
        dosage_text="5mg",
    )
    repo.save_reminder_event(event)

    ack_time = datetime(2026, 2, 24, 12, 5, tzinfo=UTC)
    updated = mark_meal_confirmation(
        event_id="e1",
        confirmed=True,
        confirmed_at=ack_time,
        repository=repo,
    )
    assert updated.status == "acknowledged"
    assert updated.meal_confirmation == "yes"
    assert updated.ack_at == ack_time
