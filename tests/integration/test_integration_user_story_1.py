"""Tests for integration user story 1."""

from datetime import date, datetime

from dietary_guardian.domain.identity.models import (
    MedicalCondition,
    Medication,
    UserProfile,
)
from dietary_guardian.domain.notifications.models import MedicationRegimen
from dietary_guardian.infrastructure.persistence import SQLiteRepository
from dietary_guardian.domain.medications import (
    compute_mcr,
    generate_daily_reminders,
    mark_meal_confirmation,
)
from dietary_guardian.application.notifications.alert_dispatch import dispatch_reminder


def test_user_story_1_schedule_notify_confirm(tmp_path) -> None:
    repo = SQLiteRepository(str(tmp_path / "int1.db"))
    user = UserProfile(
        id="u1",
        name="Mr Tan",
        age=68,
        conditions=[MedicalCondition(name="Diabetes", severity="High")],
        medications=[Medication(name="Metformin", dosage="500mg")],
    )
    regimen = MedicationRegimen(
        id="r1",
        user_id="u1",
        medication_name="Metformin",
        dosage_text="500mg",
        timing_type="pre_meal",
        offset_minutes=30,
        slot_scope=["lunch"],
    )

    reminders = generate_daily_reminders(user, [regimen], date(2026, 2, 24))
    repo.save_reminder_event(reminders[0])
    delivery = dispatch_reminder(reminders[0], ["in_app", "push"], force_push_fail=False)
    assert delivery[0].success is True

    mark_meal_confirmation(reminders[0].id, True, datetime(2026, 2, 24, 12, 5), repo)
    metrics = compute_mcr(repo.list_reminder_events("u1"))
    assert metrics.meal_confirmation_rate == 1.0
