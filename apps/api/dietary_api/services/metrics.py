"""API helpers for lightweight metric-trend reads."""

from __future__ import annotations

from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.schemas import MetricTrendListResponse, MetricTrendResponse
from dietary_guardian.domain.metrics import (
    adherence_rate_points,
    biomarker_points,
    build_metric_trend,
    meal_calorie_points,
)


def list_metric_trends_for_session(
    *,
    context: AppContext,
    user_id: str,
    metric_names: list[str],
) -> MetricTrendListResponse:
    readings = context.stores.biomarkers.list_biomarker_readings(user_id)
    meals = context.stores.meals.list_meal_records(user_id)
    adherence = context.stores.medications.list_medication_adherence_events(user_id=user_id)
    items: list[MetricTrendResponse] = []
    requested = metric_names or ["meal:calories", "adherence:rate"]
    for metric in requested:
        if metric == "meal:calories":
            trend = build_metric_trend(metric, meal_calorie_points(meals))
        elif metric == "adherence:rate":
            trend = build_metric_trend(metric, adherence_rate_points(adherence))
        elif metric.startswith("biomarker:"):
            trend = build_metric_trend(metric, biomarker_points(readings, biomarker_name=metric.split(":", 1)[1]))
        else:
            continue
        items.append(MetricTrendResponse.model_validate(trend.model_dump(mode="json")))
    return MetricTrendListResponse(items=items)
