"""Tests for medication regimen persistence extensions."""

from datetime import date

from dietary_guardian.features.reminders.domain.models import MedicationRegimen
from dietary_guardian.platform.persistence import SQLiteRepository


def test_medication_repository_persists_extended_regimen_fields(tmp_path) -> None:
    repo = SQLiteRepository(str(tmp_path / "medications.db"))
    regimen = MedicationRegimen(
        id="reg-1",
        user_id="user-1",
        medication_name="Metformin",
        canonical_name="metformin",
        dosage_text="500mg",
        timing_type="pre_meal",
        frequency_type="fixed_slots",
        frequency_times_per_day=2,
        time_rules=[{"kind": "before_meal", "slots": ["breakfast", "dinner"], "offset_minutes": 30}],
        offset_minutes=30,
        slot_scope=["breakfast", "dinner"],
        max_daily_doses=2,
        instructions_text="Take Metformin 500mg twice daily before meals for 5 days",
        source_type="plain_text",
        source_hash="abc123",
        start_date=date(2026, 3, 14),
        end_date=date(2026, 3, 18),
        timezone="Asia/Singapore",
        parse_confidence=0.92,
        active=True,
    )

    repo.save_medication_regimen(regimen)

    stored = repo.get_medication_regimen(user_id="user-1", regimen_id="reg-1")
    assert stored is not None
    assert stored.canonical_name == "metformin"
    assert stored.frequency_type == "fixed_slots"
    assert stored.frequency_times_per_day == 2
    assert stored.time_rules[0]["kind"] == "before_meal"
    assert stored.instructions_text == regimen.instructions_text
    assert stored.source_type == "plain_text"
    assert stored.source_hash == "abc123"
    assert stored.start_date == date(2026, 3, 14)
    assert stored.end_date == date(2026, 3, 18)
    assert stored.timezone == "Asia/Singapore"
