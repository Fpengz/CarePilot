"""
Expose chat dashboard API endpoints.

This router serves dashboard views and health metric summaries generated
from chat and tracking workflows.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from ..deps import chat_deps
from ..routes_shared import current_session, get_context, require_action

router = APIRouter(tags=["dashboard"])


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
    request: Request,
    session: dict[str, object] = Depends(current_session),
):
    require_action(session, "metrics.trends.read")
    deps = chat_deps(get_context(request), session)
    if not payload.metrics:
        return {"trends": {}}

    metric_lines: list[str] = []
    for key, metric in payload.metrics.items():
        metric_lines.append(
            f'  {json.dumps(key)}: {{"change": round({metric.last} - {metric.first}, 4), '
            f'"pct": round(({metric.last} - {metric.first}) / {metric.first} * 100, 2) if {metric.first} != 0 else 0}}'
        )

    code = "import json\nprint(json.dumps({\n" + ",\n".join(metric_lines) + "\n}))"
    print(f"[DashboardTrend] Running sandbox code:\n{code}")
    try:
        raw_output = deps.code_agent.run(code)
        print(f"[DashboardTrend] Sandbox output: {raw_output!r}")
    except Exception as exc:
        print(f"[DashboardTrend] Sandbox unavailable: {exc}")
        raw_output = ""

    try:
        computed = json.loads(raw_output)
    except Exception:
        computed = {
            key: {
                "change": round(metric.last - metric.first, 4),
                "pct": round((metric.last - metric.first) / metric.first * 100, 2) if metric.first else 0,
            }
            for key, metric in payload.metrics.items()
        }

    trends = {
        key: {
            **vals,
            "direction": "up" if vals["change"] > 0 else ("down" if vals["change"] < 0 else "flat"),
        }
        for key, vals in computed.items()
    }

    return {"trends": trends}
