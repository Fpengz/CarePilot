"""Tests for mcr metrics."""

from datetime import datetime

from dietary_guardian.domain.notifications.models import ReminderEvent
from dietary_guardian.domain.medications import compute_mcr


def test_compute_mcr_zero_denominator() -> None:
    metrics = compute_mcr([])
    assert metrics.reminders_sent == 0
    assert metrics.meal_confirmation_rate == 0


def test_compute_mcr_mixed_responses() -> None:
    events = [
        ReminderEvent(id="1", user_id="u", medication_name="A", scheduled_at=datetime(2026, 2, 24, 8, 0), dosage_text="5mg", meal_confirmation="yes"),
        ReminderEvent(id="2", user_id="u", medication_name="A", scheduled_at=datetime(2026, 2, 24, 12, 0), dosage_text="5mg", meal_confirmation="no"),
        ReminderEvent(id="3", user_id="u", medication_name="A", scheduled_at=datetime(2026, 2, 24, 20, 0), dosage_text="5mg", meal_confirmation="yes"),
    ]
    metrics = compute_mcr(events)
    assert metrics.reminders_sent == 3
    assert metrics.meal_confirmed_yes == 2
    assert abs(metrics.meal_confirmation_rate - (2 / 3)) < 1e-9
