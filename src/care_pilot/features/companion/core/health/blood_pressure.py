"""
Deterministic blood pressure analytics for companion workflows.

This module provides summary statistics, trend detection, and risk flags.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from care_pilot.features.companion.core.health.models import (
    BloodPressureAbnormal,
    BloodPressureReading,
    BloodPressureStats,
    BloodPressureSummary,
    BloodPressureTrend,
)

DIABETES_TARGET_SYSTOLIC = 130
DIABETES_TARGET_DIASTOLIC = 80
HIGH_RISK_SYSTOLIC = 140
HIGH_RISK_DIASTOLIC = 90
VERY_HIGH_SYSTOLIC = 160
VERY_HIGH_DIASTOLIC = 100


@dataclass(frozen=True, slots=True)
class BloodPressureTargets:
    systolic: int
    diastolic: int


def resolve_bp_targets(conditions: list[str]) -> BloodPressureTargets:
    lowered = " ".join(conditions).lower()
    if "diabetes" in lowered:
        return BloodPressureTargets(
            systolic=DIABETES_TARGET_SYSTOLIC, diastolic=DIABETES_TARGET_DIASTOLIC
        )
    return BloodPressureTargets(systolic=HIGH_RISK_SYSTOLIC, diastolic=HIGH_RISK_DIASTOLIC)


def summarize_blood_pressure(
    readings: list[BloodPressureReading], *, conditions: list[str]
) -> BloodPressureSummary | None:
    if not readings:
        return None
    ordered = sorted(readings, key=lambda item: item.recorded_at)
    systolic_values = [float(item.systolic) for item in ordered]
    diastolic_values = [float(item.diastolic) for item in ordered]
    stats = BloodPressureStats(
        avg_systolic=round(sum(systolic_values) / len(systolic_values), 1),
        avg_diastolic=round(sum(diastolic_values) / len(diastolic_values), 1),
        min_systolic=min(systolic_values),
        max_systolic=max(systolic_values),
        min_diastolic=min(diastolic_values),
        max_diastolic=max(diastolic_values),
        total_readings=len(ordered),
        start_date=ordered[0].recorded_at.date(),
        end_date=ordered[-1].recorded_at.date(),
    )

    midpoint = max(len(ordered) // 2, 1)
    first_half = ordered[:midpoint]
    second_half = ordered[midpoint:]
    avg_first = sum(item.systolic for item in first_half) / len(first_half)
    avg_second = sum(item.systolic for item in second_half) / len(second_half)
    delta = round(avg_second - avg_first, 1)
    if abs(delta) < 3:
        direction = "flat"
    elif delta > 0:
        direction = "increase"
    else:
        direction = "decrease"
    trend = BloodPressureTrend(direction=direction, delta_systolic=delta)

    targets = resolve_bp_targets(conditions)
    abnormal: list[BloodPressureAbnormal] = []
    for item in ordered:
        if item.systolic >= HIGH_RISK_SYSTOLIC or item.diastolic >= HIGH_RISK_DIASTOLIC:
            level = (
                "high"
                if item.systolic >= VERY_HIGH_SYSTOLIC or item.diastolic >= VERY_HIGH_DIASTOLIC
                else "elevated"
            )
            abnormal.append(
                BloodPressureAbnormal(
                    recorded_at=item.recorded_at,
                    systolic=float(item.systolic),
                    diastolic=float(item.diastolic),
                    level=level,
                )
            )

    has_high_bp = (
        stats.avg_systolic >= HIGH_RISK_SYSTOLIC
        or stats.avg_diastolic >= HIGH_RISK_DIASTOLIC
        or len(abnormal) > 0
    )
    above_target = stats.avg_systolic >= targets.systolic or stats.avg_diastolic >= targets.diastolic
    return BloodPressureSummary(
        stats=stats,
        trend=trend,
        target_systolic=targets.systolic,
        target_diastolic=targets.diastolic,
        above_target=above_target,
        has_high_bp=has_high_bp,
        abnormal_readings=abnormal,
    )


def bp_metric_points(readings: list[BloodPressureReading], *, metric: str) -> list[tuple[datetime, float]]:
    if metric not in {"systolic", "diastolic"}:
        raise ValueError("metric must be 'systolic' or 'diastolic'")
    ordered = sorted(readings, key=lambda item: item.recorded_at)
    if metric == "systolic":
        return [(item.recorded_at, float(item.systolic)) for item in ordered]
    return [(item.recorded_at, float(item.diastolic)) for item in ordered]


def build_bp_chart_points(
    readings: list[BloodPressureReading],
    *,
    start: date,
    end: date,
    timezone_name: str,
    bucket: str,
) -> list[dict[str, object]]:
    if bucket not in {"day", "week"}:
        raise ValueError("bucket must be 'day' or 'week'")
    tz = ZoneInfo(timezone_name)

    def _bucket_start(value: datetime) -> datetime:
        local = value.astimezone(tz)
        if bucket == "day":
            return local.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = local.date() - timedelta(days=local.date().weekday())
        return datetime.combine(week_start, time.min, tzinfo=tz)

    totals: dict[datetime, dict[str, float]] = defaultdict(
        lambda: {"systolic": 0.0, "diastolic": 0.0, "count": 0.0}
    )
    for item in readings:
        local_date = item.recorded_at.astimezone(tz).date()
        if start <= local_date <= end:
            key = _bucket_start(item.recorded_at)
            totals[key]["systolic"] += float(item.systolic)
            totals[key]["diastolic"] += float(item.diastolic)
            totals[key]["count"] += 1.0

    windows: list[datetime] = []
    if bucket == "day":
        for offset in range((end - start).days + 1):
            day = start + timedelta(days=offset)
            windows.append(datetime.combine(day, time.min, tzinfo=tz))
    else:
        cursor = start - timedelta(days=start.weekday())
        final = end - timedelta(days=end.weekday())
        while cursor <= final:
            windows.append(datetime.combine(cursor, time.min, tzinfo=tz))
            cursor += timedelta(days=7)

    points: list[dict[str, object]] = []
    for start_dt in windows:
        data = totals.get(start_dt)
        if data and data["count"]:
            systolic = round(data["systolic"] / data["count"], 1)
            diastolic = round(data["diastolic"] / data["count"], 1)
        else:
            systolic = 0.0
            diastolic = 0.0
        end_dt = start_dt + (timedelta(days=1) if bucket == "day" else timedelta(days=7))
        if bucket == "day":
            label = start_dt.strftime("%b %d")
        else:
            week_end = start_dt + timedelta(days=6)
            label = f"{start_dt.strftime('%b %d')} - {week_end.strftime('%b %d')}"
        points.append(
            {
                "bucket_start": start_dt,
                "bucket_end": end_dt,
                "label": label,
                "systolic": systolic,
                "diastolic": diastolic,
            }
        )
    return points


__all__ = [
    "BloodPressureTargets",
    "build_bp_chart_points",
    "bp_metric_points",
    "resolve_bp_targets",
    "summarize_blood_pressure",
]
