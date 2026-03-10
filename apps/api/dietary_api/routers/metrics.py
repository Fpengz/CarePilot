"""API router for metrics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from ..routes_shared import current_session, get_context, require_action
from ..schemas import MetricTrendListResponse
from ..services.metrics import list_metric_trends_for_session

router = APIRouter(tags=["metrics"])


@router.get("/api/v1/metrics/trends", response_model=MetricTrendListResponse)
def metrics_trends(
    request: Request,
    metric: list[str] = Query(default=[]),
    session: dict[str, object] = Depends(current_session),
) -> MetricTrendListResponse:
    require_action(session, "metrics.trends.read")
    return list_metric_trends_for_session(
        context=get_context(request),
        user_id=str(session["user_id"]),
        metric_names=metric,
    )
