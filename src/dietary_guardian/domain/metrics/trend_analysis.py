"""Deterministic trend analysis helpers for longitudinal health metrics."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from dietary_guardian.domain.health.models import (
    BiomarkerReading,
    MedicationAdherenceEvent,
    MetricPoint,
    MetricTrend,
)
from dietary_guardian.domain.nutrition.meal_record_accessors import meal_nutrition
from dietary_guardian.domain.meals.recognition import MealRecognitionRecord


def _sorted_points(points: list[MetricPoint]) -> list[MetricPoint]:
    return sorted(points, key=lambda item: item.timestamp)


def build_metric_trend(metric: str, points: list[MetricPoint]) -> MetricTrend:
    ordered = _sorted_points(points)
    if not ordered:
        return MetricTrend(metric=metric)

    first = ordered[0].value
    last = ordered[-1].value
    delta = round(last - first, 4)
    if first == 0:
        percent_change = None
    else:
        percent_change = round(((last - first) / abs(first)) * 100.0, 4)
    slope = round((last - first) / max(len(ordered) - 1, 1), 4)
    direction = "flat"
    if delta > 0:
        direction = "increase"
    elif delta < 0:
        direction = "decrease"
    return MetricTrend(
        metric=metric,
        points=ordered,
        delta=delta,
        percent_change=percent_change,
        slope_per_point=slope,
        direction=direction,
    )


def biomarker_points(readings: list[BiomarkerReading], *, biomarker_name: str) -> list[MetricPoint]:
    target = biomarker_name.lower()
    out: list[MetricPoint] = []
    for reading in readings:
        if reading.name.lower() != target:
            continue
        measured_at = reading.measured_at or datetime.now(timezone.utc)
        out.append(MetricPoint(timestamp=measured_at, value=float(reading.value)))
    return out


def meal_calorie_points(records: list[MealRecognitionRecord]) -> list[MetricPoint]:
    by_day: dict[str, float] = defaultdict(float)
    for record in records:
        key = record.captured_at.date().isoformat()
        by_day[key] += float(meal_nutrition(record).calories)
    points: list[MetricPoint] = []
    for day, value in by_day.items():
        points.append(MetricPoint(timestamp=datetime.fromisoformat(f"{day}T00:00:00+00:00"), value=round(value, 4)))
    return _sorted_points(points)


def adherence_rate_points(events: list[MedicationAdherenceEvent]) -> list[MetricPoint]:
    buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"taken": 0, "total": 0})
    for event in events:
        day = event.scheduled_at.date().isoformat()
        buckets[day]["total"] += 1
        if event.status == "taken":
            buckets[day]["taken"] += 1
    points: list[MetricPoint] = []
    for day, agg in buckets.items():
        total = agg["total"]
        rate = (agg["taken"] / total) if total else 0.0
        points.append(MetricPoint(timestamp=datetime.fromisoformat(f"{day}T00:00:00+00:00"), value=round(rate, 4)))
    return _sorted_points(points)
