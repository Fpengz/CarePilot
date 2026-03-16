"""Tests for blood pressure analytics."""

from datetime import UTC, datetime

from care_pilot.features.companion.core.health.blood_pressure import (
    resolve_bp_targets,
    summarize_blood_pressure,
)
from care_pilot.features.companion.core.health.models import BloodPressureReading


def _reading(ts: str, systolic: float, diastolic: float) -> BloodPressureReading:
    return BloodPressureReading(
        recorded_at=datetime.fromisoformat(ts).replace(tzinfo=UTC),
        systolic=systolic,
        diastolic=diastolic,
    )


def test_bp_summary_detects_trend_and_abnormal() -> None:
    readings = [
        _reading("2026-03-01T08:00:00", 128, 78),
        _reading("2026-03-02T08:00:00", 138, 88),
        _reading("2026-03-03T08:00:00", 165, 102),
        _reading("2026-03-04T08:00:00", 150, 95),
    ]
    summary = summarize_blood_pressure(readings, conditions=["type 2 diabetes"])
    assert summary is not None
    assert summary.stats.total_readings == 4
    assert summary.trend.direction == "increase"
    assert summary.has_high_bp is True
    assert summary.abnormal_readings
    assert summary.abnormal_readings[-1].level in {"elevated", "high"}
    assert summary.target_systolic == 130


def test_bp_targets_use_diabetes_rule() -> None:
    targets = resolve_bp_targets(["Type 2 Diabetes"])
    assert targets.systolic == 130
    assert targets.diastolic == 80
