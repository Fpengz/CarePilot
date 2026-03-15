"""Dashboard aggregation service."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from statistics import mean
from typing import Literal

from fastapi import HTTPException

from care_pilot.features.companion.core.health.models import (
    BiomarkerReading,
    HealthProfileRecord,
    MedicationAdherenceEvent,
)
from care_pilot.features.meals.domain.models import (
    NutritionRiskProfile,
    ValidatedMealEvent,
)
from care_pilot.features.reminders.domain.models import ReminderEvent

from ..deps import AppContext
from ..schemas import (
    DashboardAlertResponse,
    DashboardBucket,
    DashboardChartsResponse,
    DashboardInsightsResponse,
    DashboardMacroChartResponse,
    DashboardMacroPointResponse,
    DashboardMealTimingBinResponse,
    DashboardMealTimingChartResponse,
    DashboardMetricChartResponse,
    DashboardOverviewResponse,
    DashboardRangeResponse,
    DashboardSeriesPointResponse,
    DashboardSummaryMetricResponse,
    DashboardSummaryResponse,
)


@dataclass(frozen=True, slots=True)
class _ResolvedRange:
    key: str
    label: str
    start: date
    end: date
    bucket: DashboardBucket

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def to_response(self) -> DashboardRangeResponse:
        return DashboardRangeResponse(
            key=self.key,
            label=self.label,
            **{"from": self.start},
            to=self.end,
            bucket=self.bucket,
            days=self.days,
        )


def _start_of_day(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


def _end_of_day(value: date) -> datetime:
    return datetime.combine(value, time.max, tzinfo=UTC)


def _start_of_week(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _resolve_bucket(*, key: str, start: date, end: date) -> DashboardBucket:
    span_days = (end - start).days + 1
    if key == "today":
        return "hour"
    if span_days <= 30:
        return "day"
    return "week"


def _resolve_range(
    *,
    range_key: str,
    from_date: date | None,
    to_date: date | None,
    today: date | None = None,
) -> _ResolvedRange:
    anchor = today or datetime.now(UTC).date()
    presets: dict[str, tuple[str, int]] = {
        "today": ("Today", 1),
        "7d": ("Last 7 Days", 7),
        "30d": ("Last 30 Days", 30),
        "3m": ("Last 3 Months", 90),
        "1y": ("Last Year", 365),
    }
    if range_key == "custom":
        if from_date is None or to_date is None:
            raise HTTPException(
                status_code=400, detail="custom range requires from and to"
            )
        if from_date > to_date:
            raise HTTPException(
                status_code=400, detail="from must be before to"
            )
        return _ResolvedRange(
            key="custom",
            label="Custom Range",
            start=from_date,
            end=to_date,
            bucket=_resolve_bucket(key="custom", start=from_date, end=to_date),
        )
    if range_key not in presets:
        raise HTTPException(
            status_code=400, detail="unsupported dashboard range"
        )
    label, days = presets[range_key]
    start = anchor - timedelta(days=days - 1)
    return _ResolvedRange(
        key=range_key,
        label=label,
        start=start,
        end=anchor,
        bucket=_resolve_bucket(key=range_key, start=start, end=anchor),
    )


def _comparison_range(current: _ResolvedRange) -> _ResolvedRange:
    end = current.start - timedelta(days=1)
    start = end - timedelta(days=current.days - 1)
    return _ResolvedRange(
        key=f"{current.key}_comparison",
        label=f"Previous {current.label}",
        start=start,
        end=end,
        bucket=current.bucket,
    )


def _bucket_start(value: datetime, bucket: DashboardBucket) -> datetime:
    ts = value.astimezone(UTC)
    if bucket == "hour":
        return ts.replace(minute=0, second=0, microsecond=0)
    if bucket == "day":
        return ts.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = _start_of_week(ts.date())
    return _start_of_day(week_start)


def _bucket_end(start: datetime, bucket: DashboardBucket) -> datetime:
    if bucket == "hour":
        return start + timedelta(hours=1)
    if bucket == "day":
        return start + timedelta(days=1)
    return start + timedelta(days=7)


def _bucket_label(start: datetime, bucket: DashboardBucket) -> str:
    if bucket == "hour":
        return start.strftime("%H:%M")
    if bucket == "day":
        return start.strftime("%b %d")
    week_end = start + timedelta(days=6)
    return f"{start.strftime('%b %d')} - {week_end.strftime('%b %d')}"


def _series_windows(current: _ResolvedRange) -> list[datetime]:
    if current.bucket == "hour":
        anchor = _start_of_day(current.start)
        return [anchor + timedelta(hours=hour) for hour in range(24)]
    if current.bucket == "day":
        anchor = current.start
        return [
            _start_of_day(anchor + timedelta(days=offset))
            for offset in range(current.days)
        ]

    windows: list[datetime] = []
    cursor = _start_of_day(_start_of_week(current.start))
    final = _start_of_day(_start_of_week(current.end))
    while cursor <= final:
        windows.append(cursor)
        cursor += timedelta(days=7)
    return windows


def _filter_profiles(
    profiles: list[NutritionRiskProfile],
    *,
    start: date,
    end: date,
) -> list[NutritionRiskProfile]:
    return [
        item
        for item in profiles
        if start <= item.captured_at.astimezone(UTC).date() <= end
    ]


def _filter_events(
    events: (
        list[MedicationAdherenceEvent]
        | list[ReminderEvent]
        | list[ValidatedMealEvent]
    ),
    *,
    start: date,
    end: date,
    accessor: str,
) -> list:
    out = []
    for item in events:
        value = getattr(item, accessor)
        if start <= value.astimezone(UTC).date() <= end:
            out.append(item)
    return out


def _risk_score(profile: NutritionRiskProfile) -> float:
    score = 22.0
    if "high_hba1c" in profile.risk_tags:
        score += 30.0
    if "high_ldl" in profile.risk_tags:
        score += 18.0
    if "high_bp" in profile.risk_tags:
        score += 12.0
    if profile.sugar_g >= 15:
        score += 10.0
    if profile.carbs_g >= 70:
        score += 8.0
    return min(score, 100.0)


def _direction(delta: float) -> Literal["up", "down", "flat"]:
    if delta > 0:
        return "up"
    if delta < 0:
        return "down"
    return "flat"


def _safe_pct_delta(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return round(((current - previous) / abs(previous)) * 100.0, 2)


def _calorie_target(profile: HealthProfileRecord | None) -> float:
    if profile and profile.target_calories_per_day:
        return float(profile.target_calories_per_day)
    return 1800.0


def _build_calorie_chart(
    windows: list[datetime],
    bucket: DashboardBucket,
    profiles: list[NutritionRiskProfile],
    *,
    calorie_target: float,
) -> DashboardMetricChartResponse:
    totals: dict[datetime, float] = defaultdict(float)
    for item in profiles:
        totals[_bucket_start(item.captured_at, bucket)] += float(item.calories)
    points = [
        DashboardSeriesPointResponse(
            bucket_start=start,
            bucket_end=_bucket_end(start, bucket),
            label=_bucket_label(start, bucket),
            value=round(totals.get(start, 0.0), 2),
            target=round(
                calorie_target if bucket != "week" else calorie_target * 7, 2
            ),
        )
        for start in windows
    ]
    return DashboardMetricChartResponse(
        title="Daily Calorie Intake", bucket=bucket, points=points
    )


def _build_macro_chart(
    windows: list[datetime],
    bucket: DashboardBucket,
    profiles: list[NutritionRiskProfile],
) -> DashboardMacroChartResponse:
    totals: dict[datetime, dict[str, float]] = defaultdict(
        lambda: {"protein": 0.0, "carbs": 0.0, "fat": 0.0, "calories": 0.0}
    )
    for item in profiles:
        bucket_key = _bucket_start(item.captured_at, bucket)
        totals[bucket_key]["protein"] += float(item.protein_g)
        totals[bucket_key]["carbs"] += float(item.carbs_g)
        totals[bucket_key]["fat"] += float(item.fat_g)
        totals[bucket_key]["calories"] += float(item.calories)
    points = [
        DashboardMacroPointResponse(
            bucket_start=start,
            bucket_end=_bucket_end(start, bucket),
            label=_bucket_label(start, bucket),
            protein_g=round(totals.get(start, {}).get("protein", 0.0), 2),
            carbs_g=round(totals.get(start, {}).get("carbs", 0.0), 2),
            fat_g=round(totals.get(start, {}).get("fat", 0.0), 2),
            calories=round(totals.get(start, {}).get("calories", 0.0), 2),
        )
        for start in windows
    ]
    return DashboardMacroChartResponse(
        title="Nutrition Balance", bucket=bucket, points=points
    )


def _build_risk_chart(
    windows: list[datetime],
    bucket: DashboardBucket,
    profiles: list[NutritionRiskProfile],
) -> DashboardMetricChartResponse:
    grouped: dict[datetime, list[float]] = defaultdict(list)
    for item in profiles:
        grouped[_bucket_start(item.captured_at, bucket)].append(
            _risk_score(item)
        )
    points = [
        DashboardSeriesPointResponse(
            bucket_start=start,
            bucket_end=_bucket_end(start, bucket),
            label=_bucket_label(start, bucket),
            value=round(mean(grouped.get(start, [0.0])), 2),
        )
        for start in windows
    ]
    return DashboardMetricChartResponse(
        title="Glycemic Risk Trend", bucket=bucket, points=points
    )


def _build_adherence_chart(
    windows: list[datetime],
    bucket: DashboardBucket,
    events: list[MedicationAdherenceEvent],
) -> DashboardMetricChartResponse:
    grouped: dict[datetime, dict[str, int]] = defaultdict(
        lambda: {"taken": 0, "total": 0}
    )
    for item in events:
        bucket_key = _bucket_start(item.scheduled_at, bucket)
        grouped[bucket_key]["total"] += 1
        if item.status == "taken":
            grouped[bucket_key]["taken"] += 1
    points = []
    for start in windows:
        data = grouped.get(start, {"taken": 0, "total": 0})
        rate = (
            (data["taken"] / data["total"]) * 100.0 if data["total"] else 0.0
        )
        points.append(
            DashboardSeriesPointResponse(
                bucket_start=start,
                bucket_end=_bucket_end(start, bucket),
                label=_bucket_label(start, bucket),
                value=round(rate, 2),
                target=90.0,
            )
        )
    return DashboardMetricChartResponse(
        title="Medication Adherence", bucket=bucket, points=points
    )


def _build_meal_timing_chart(
    meals: list[ValidatedMealEvent],
) -> DashboardMealTimingChartResponse:
    counts = [0] * 24
    for meal in meals:
        counts[meal.captured_at.astimezone(UTC).hour] += 1
    bins = [
        DashboardMealTimingBinResponse(
            hour=hour, label=f"{hour:02d}:00", count=count
        )
        for hour, count in enumerate(counts)
    ]
    return DashboardMealTimingChartResponse(
        title="Meal Timing Distribution", bins=bins
    )


def _average_daily_calories(
    profiles: list[NutritionRiskProfile], days: int
) -> float:
    if days <= 0:
        return 0.0
    return sum(item.calories for item in profiles) / days


def _adherence_rate(events: list[MedicationAdherenceEvent]) -> float:
    if not events:
        return 0.0
    taken = sum(1 for item in events if item.status == "taken")
    return taken / len(events)


def _latest_value(readings: list[BiomarkerReading], name: str) -> float | None:
    filtered = [item for item in readings if item.name.lower() == name.lower()]
    if not filtered:
        return None
    filtered.sort(
        key=lambda item: item.measured_at or datetime.min.replace(tzinfo=UTC)
    )
    return float(filtered[-1].value)


def _build_summary(
    *,
    current_profiles: list[NutritionRiskProfile],
    previous_profiles: list[NutritionRiskProfile],
    current_adherence: list[MedicationAdherenceEvent],
    previous_adherence: list[MedicationAdherenceEvent],
    readings: list[BiomarkerReading],
    calorie_target: float,
    days: int,
) -> DashboardSummaryResponse:
    avg_daily_calories = _average_daily_calories(current_profiles, days)
    previous_daily_calories = _average_daily_calories(
        previous_profiles, max(days, 1)
    )
    calorie_score = max(
        0.0,
        100.0
        - (abs(avg_daily_calories - calorie_target) / calorie_target * 100.0),
    )
    previous_calorie_score = max(
        0.0,
        100.0
        - (
            abs(previous_daily_calories - calorie_target)
            / calorie_target
            * 100.0
        ),
    )
    calorie_delta = round(calorie_score - previous_calorie_score, 2)

    adherence_pct = _adherence_rate(current_adherence) * 100.0
    previous_adherence_pct = _adherence_rate(previous_adherence) * 100.0
    adherence_delta = round(adherence_pct - previous_adherence_pct, 2)

    risk_values = [_risk_score(item) for item in current_profiles]
    previous_risk_values = [_risk_score(item) for item in previous_profiles]
    risk_avg = mean(risk_values) if risk_values else 0.0
    previous_risk_avg = (
        mean(previous_risk_values) if previous_risk_values else 0.0
    )
    risk_delta = round(risk_avg - previous_risk_avg, 2)
    risk_status = (
        "stable" if risk_avg < 40 else "watch" if risk_avg < 60 else "elevated"
    )

    hba1c = _latest_value(readings, "hba1c")
    calorie_variance = (
        abs(avg_daily_calories - calorie_target) / calorie_target
        if calorie_target
        else 0.0
    )
    stability = max(
        0.0, 100.0 - (calorie_variance * 50.0) - (100.0 - adherence_pct) * 0.4
    )
    stability_status = (
        "steady"
        if stability >= 75
        else "watch" if stability >= 55 else "fragile"
    )

    return DashboardSummaryResponse(
        nutrition_goal_score=DashboardSummaryMetricResponse(
            label="Nutrition Goal Score",
            value=round(calorie_score, 2),
            unit="%",
            delta=calorie_delta,
            direction=_direction(calorie_delta),
            detail=f"Average {avg_daily_calories:.0f} kcal/day against a {calorie_target:.0f} kcal target.",
        ),
        adherence_score=DashboardSummaryMetricResponse(
            label="Adherence Score",
            value=round(adherence_pct, 2),
            unit="%",
            delta=adherence_delta,
            direction=_direction(adherence_delta),
            detail=f"{sum(1 for item in current_adherence if item.status == 'taken')} of {len(current_adherence)} doses taken in range.",
        ),
        glycemic_risk=DashboardSummaryMetricResponse(
            label="Glycemic Risk",
            value=round(risk_avg, 2),
            unit="/100",
            delta=risk_delta,
            direction=_direction(-risk_delta),
            status=risk_status,
            detail=(
                f"Latest HbA1c {hba1c:.1f}."
                if hba1c is not None
                else "No HbA1c reading available yet."
            ),
        ),
        stability_index=DashboardSummaryMetricResponse(
            label="Stability Index",
            value=round(stability, 2),
            unit="%",
            status=stability_status,
            detail="Combines intake consistency and medication follow-through.",
        ),
    )


def _build_alerts(
    *,
    summary: DashboardSummaryResponse,
    reminders: list[ReminderEvent],
    readings: list[BiomarkerReading],
) -> list[DashboardAlertResponse]:
    alerts: list[DashboardAlertResponse] = []
    latest_hba1c = _latest_value(readings, "hba1c")
    if latest_hba1c is not None and latest_hba1c >= 7.0:
        alerts.append(
            DashboardAlertResponse(
                id="hba1c-watch",
                severity="warning",
                title="Glycemic control still needs attention",
                detail=f"Latest HbA1c is {latest_hba1c:.1f}. Prioritize lower-sugar meal patterns this week.",
                href="/metrics",
            )
        )
    if summary.adherence_score.value < 85:
        alerts.append(
            DashboardAlertResponse(
                id="adherence-gap",
                severity="warning",
                title="Medication adherence slipped",
                detail="Dose completion is below the 85% target for this range.",
                href="/medications",
            )
        )
    if any(item.status == "missed" for item in reminders):
        alerts.append(
            DashboardAlertResponse(
                id="missed-reminder",
                severity="info",
                title="A reminder was missed in the current window",
                detail="Review reminder timing and delivery channel before the next medication cycle.",
                href="/reminders",
            )
        )
    if not alerts:
        alerts.append(
            DashboardAlertResponse(
                id="steady-state",
                severity="info",
                title="No acute alerts",
                detail="Current trends are stable enough to focus on habit consistency.",
            )
        )
    return alerts


def _build_insights(
    *,
    summary: DashboardSummaryResponse,
    calorie_target: float,
    current_profiles: list[NutritionRiskProfile],
) -> DashboardInsightsResponse:
    recommendations: list[str] = []
    key_drivers: list[str] = []
    average_calories = _average_daily_calories(
        current_profiles,
        (
            1
            if not current_profiles
            else len({item.captured_at.date() for item in current_profiles})
        ),
    )
    if summary.glycemic_risk.status in {"watch", "elevated"}:
        recommendations.append(
            "Shift one high-carb dinner this week toward a higher-protein, higher-fiber plate."
        )
        key_drivers.append(
            "Repeated high-risk meal tags are pushing glycemic risk above the target band."
        )
    if summary.adherence_score.value < 90:
        recommendations.append(
            "Tighten reminder timing around the missed dose window and keep one backup notification channel active."
        )
        key_drivers.append(
            "Medication adherence is the fastest lever to improve short-term stability."
        )
    if average_calories > calorie_target * 1.08:
        recommendations.append(
            "Trim the highest-calorie meal by 10-15% rather than cutting across the whole day."
        )
        key_drivers.append(
            "Average calorie intake is running above the configured target."
        )
    if not recommendations:
        recommendations.append(
            "Keep the current cadence and review deeper analytics only if the trend turns for two consecutive weeks."
        )
        key_drivers.append(
            "Nutrition and adherence are both inside the steady zone."
        )
    return DashboardInsightsResponse(
        recommendations=recommendations[:3], key_drivers=key_drivers[:3]
    )


def get_dashboard_overview(
    *,
    context: AppContext,
    user_id: str,
    range_key: str,
    from_date: date | None = None,
    to_date: date | None = None,
) -> DashboardOverviewResponse:
    current = _resolve_range(
        range_key=range_key, from_date=from_date, to_date=to_date
    )
    comparison = _comparison_range(current)

    profile = context.stores.profiles.get_health_profile(user_id)
    calorie_target = _calorie_target(
        profile if isinstance(profile, HealthProfileRecord) else None
    )

    all_profiles = context.stores.meals.list_nutrition_risk_profiles(user_id)
    all_adherence = (
        context.stores.medications.list_medication_adherence_events(
            user_id=user_id, limit=1000
        )
    )
    all_reminders = context.stores.reminders.list_reminder_events(user_id)
    all_meals = context.stores.meals.list_validated_meal_events(user_id)
    readings = context.stores.biomarkers.list_biomarker_readings(user_id)

    current_profiles = _filter_profiles(
        all_profiles, start=current.start, end=current.end
    )
    previous_profiles = _filter_profiles(
        all_profiles, start=comparison.start, end=comparison.end
    )
    current_adherence = _filter_events(
        all_adherence,
        start=current.start,
        end=current.end,
        accessor="scheduled_at",
    )
    previous_adherence = _filter_events(
        all_adherence,
        start=comparison.start,
        end=comparison.end,
        accessor="scheduled_at",
    )
    current_reminders = _filter_events(
        all_reminders,
        start=current.start,
        end=current.end,
        accessor="scheduled_at",
    )
    current_meals = _filter_events(
        all_meals, start=current.start, end=current.end, accessor="captured_at"
    )

    summary = _build_summary(
        current_profiles=current_profiles,
        previous_profiles=previous_profiles,
        current_adherence=current_adherence,
        previous_adherence=previous_adherence,
        readings=readings,
        calorie_target=calorie_target,
        days=current.days,
    )
    windows = _series_windows(current)
    charts = DashboardChartsResponse(
        calories=_build_calorie_chart(
            windows,
            current.bucket,
            current_profiles,
            calorie_target=calorie_target,
        ),
        macros=_build_macro_chart(windows, current.bucket, current_profiles),
        glycemic_risk=_build_risk_chart(
            windows, current.bucket, current_profiles
        ),
        adherence=_build_adherence_chart(
            windows, current.bucket, current_adherence
        ),
        meal_timing=_build_meal_timing_chart(current_meals),
    )
    return DashboardOverviewResponse(
        range=current.to_response(),
        comparison_range=comparison.to_response(),
        summary=summary,
        alerts=_build_alerts(
            summary=summary, reminders=current_reminders, readings=readings
        ),
        charts=charts,
        insights=_build_insights(
            summary=summary,
            calorie_target=calorie_target,
            current_profiles=current_profiles,
        ),
    )
