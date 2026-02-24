from datetime import datetime

from dietary_guardian.models.analytics import EngagementMetrics
from dietary_guardian.models.medication import ReminderEvent
from dietary_guardian.services.dashboard_service import build_analytics_summary


def test_dashboard_metrics_summary() -> None:
    metrics = EngagementMetrics(reminders_sent=4, meal_confirmed_yes=3, meal_confirmed_no=1, meal_confirmation_rate=0.75)
    reminders = [
        ReminderEvent(id="1", user_id="u", medication_name="A", scheduled_at=datetime(2026, 2, 24, 8), dosage_text="5mg", status="acknowledged"),
        ReminderEvent(id="2", user_id="u", medication_name="A", scheduled_at=datetime(2026, 2, 24, 12), dosage_text="5mg", status="acknowledged"),
        ReminderEvent(id="3", user_id="u", medication_name="A", scheduled_at=datetime(2026, 2, 24, 20), dosage_text="5mg", status="sent"),
        ReminderEvent(id="4", user_id="u", medication_name="A", scheduled_at=datetime(2026, 2, 24, 22), dosage_text="5mg", status="missed"),
    ]
    summary = build_analytics_summary(metrics, reminders)
    assert summary["mcr"] == 0.75
    assert summary["acknowledged"] == 2.0
