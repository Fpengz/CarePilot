"""
Expose chat dashboard API endpoints.

This router serves dashboard views and health metric summaries generated
from chat and tracking workflows.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from ..deps import chat_deps
from ..routes_shared import current_session, get_context, require_action
from ..schemas import DashboardOverviewResponse
from ..services.dashboard import get_dashboard_overview

router = APIRouter(tags=["dashboard"])


@router.get("/api/v1/dashboard", response_model=DashboardOverviewResponse)
def dashboard_overview(
    request: Request,
    range: str = Query(default="30d"),
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    session: dict[str, object] = Depends(current_session),
) -> DashboardOverviewResponse:
    require_action(session, "dashboard.read")
    return get_dashboard_overview(
        context=get_context(request),
        user_id=str(session["user_id"]),
        range_key=range,
        from_date=None if from_date is None else date.fromisoformat(from_date),
        to_date=None if to_date is None else date.fromisoformat(to_date),
    )


class MetricBound(BaseModel):
    first: float
    last: float
    unit: str = ""


class TrendRequest(BaseModel):
    metrics: dict[str, MetricBound]


@router.get("/api/v1/dashboard/entries")
def dashboard_entries(
    request: Request,
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    session: dict[str, object] = Depends(current_session),
):
    require_action(session, "metrics.trends.read")
    deps = chat_deps(get_context(request), session)
    raw = deps.health_tracker.get_raw_entries(start, end)
    return {
        "entries": [
            {
                "datetime": row["created_at"][:16].replace("T", " "),
                "message": row["content"],
            }
            for row in raw
        ]
    }


@router.get("/api/v1/dashboard/chart-data")
def dashboard_chart_data(
    request: Request,
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD"),
    session: dict[str, object] = Depends(current_session),
):
    require_action(session, "metrics.trends.read")
    deps = chat_deps(get_context(request), session)
    return deps.health_tracker.get_chart_data(start, end)


@router.post("/api/v1/dashboard/trend")
def dashboard_trend(
    payload: TrendRequest,
    session: dict[str, object] = Depends(current_session),
):
    require_action(session, "metrics.trends.read")
    if not payload.metrics:
        return {"trends": {}}

    computed = {}
    for key, metric in payload.metrics.items():
        change = round(metric.last - metric.first, 4)
        pct = round((change / metric.first) * 100, 2) if metric.first != 0 else 0
        computed[key] = {
            "change": change,
            "pct": pct,
        }

    trends = {
        key: {
            **vals,
            "direction": "up" if vals["change"] > 0 else ("down" if vals["change"] < 0 else "flat"),
        }
        for key, vals in computed.items()
    }

    return {"trends": trends}
