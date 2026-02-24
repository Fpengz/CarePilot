from datetime import datetime

from dietary_guardian.models.medication import ReminderEvent
from dietary_guardian.services.dashboard_service import build_role_medication_view


def test_role_medication_views() -> None:
    reminders = [
        ReminderEvent(id="1", user_id="u", medication_name="A", scheduled_at=datetime(2026, 2, 24, 8), dosage_text="5mg", status="sent"),
        ReminderEvent(id="2", user_id="u", medication_name="A", scheduled_at=datetime(2026, 2, 24, 12), dosage_text="5mg", status="missed"),
        ReminderEvent(id="3", user_id="u", medication_name="A", scheduled_at=datetime(2026, 2, 24, 20), dosage_text="5mg", status="acknowledged"),
    ]
    assert build_role_medication_view("patient", reminders)["due_now"] == 1
    assert build_role_medication_view("caregiver", reminders)["missed"] == 1
    assert build_role_medication_view("clinician", reminders)["acknowledged"] == 1
