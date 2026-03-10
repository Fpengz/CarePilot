from datetime import datetime

from dietary_guardian.application.impact.view_helpers import build_profile_mode_medication_view
from dietary_guardian.domain.notifications.models import ReminderEvent


def test_profile_mode_medication_views() -> None:
    reminders = [
        ReminderEvent(id="1", user_id="u", medication_name="A", scheduled_at=datetime(2026, 2, 24, 8), dosage_text="5mg", status="sent"),
        ReminderEvent(id="2", user_id="u", medication_name="A", scheduled_at=datetime(2026, 2, 24, 12), dosage_text="5mg", status="missed"),
        ReminderEvent(id="3", user_id="u", medication_name="A", scheduled_at=datetime(2026, 2, 24, 20), dosage_text="5mg", status="acknowledged"),
    ]
    assert build_profile_mode_medication_view("self", reminders)["due_now"] == 1
    assert build_profile_mode_medication_view("caregiver", reminders)["missed"] == 1
