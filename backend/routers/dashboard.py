"""
backend/routers/dashboard.py
-----------------------------
Endpoints:
    GET /api/dashboard/entries?start=YYYY-MM-DD&end=YYYY-MM-DD
        — raw [TRACK] messages in the date range

    GET /api/dashboard/chart-data?start=YYYY-MM-DD&end=YYYY-MM-DD
        — parsed & grouped metric data ready for Recharts

    POST /api/dashboard/trend
        — computes first→last change for each metric via E2B sandbox
"""
import json
from fastapi import APIRouter, Query
from pydantic import BaseModel

from backend.deps import health_tracker
from agents.code_agent import CodeAgent

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

_code_agent = CodeAgent()


class MetricBound(BaseModel):
    first: float
    last: float
    unit: str = ""


class TrendRequest(BaseModel):
    metrics: dict[str, MetricBound]


@router.get("/entries")
def get_entries(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end:   str = Query(..., description="End date YYYY-MM-DD"),
):
    """Raw [TRACK] messages logged by the user in the given date range."""
    raw = health_tracker.get_raw_entries(start, end)
    return {
        "entries": [
            {
                "datetime": r["created_at"][:16].replace("T", " "),
                "message":  r["content"],
            }
            for r in raw
        ]
    }


@router.get("/chart-data")
def get_chart_data(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end:   str = Query(..., description="End date YYYY-MM-DD"),
):
    """
    Returns metric data grouped by type, suitable for Recharts LineChart.

    Shape:
    {
      "metrics": {
        "weight": {
          "label": "Weight", "unit": "kg",
          "data": [{"date": "2026-03-01T10:00:00", "value": 80.5}, ...]
        },
        ...
      }
    }
    """
    return health_tracker.get_chart_data(start, end)


@router.post("/trend")
def get_trend(body: TrendRequest):
    """
    For each metric, compute the change (last − first) and % change
    by running a Python script in the E2B sandbox via CodeAgent.

    Returns:
    {
      "trends": {
        "weight": {"change": -2.0, "pct": -2.5, "direction": "down"},
        ...
      }
    }
    """
    if not body.metrics:
        return {"trends": {}}

    # Build a self-contained Python script that outputs JSON
    metric_lines = []
    for key, m in body.metrics.items():
        safe_key = key.replace("-", "_").replace(" ", "_")
        metric_lines.append(
            f'  {json.dumps(key)}: {{"change": round({m.last} - {m.first}, 4), '
            f'"pct": round(({m.last} - {m.first}) / {m.first} * 100, 2) if {m.first} != 0 else 0}}'
        )

    code = "import json\nprint(json.dumps({\n" + ",\n".join(metric_lines) + "\n}))"

    print(f"[DashboardTrend] Running sandbox code:\n{code}")
    raw_output = _code_agent.run(code)
    print(f"[DashboardTrend] Sandbox output: {raw_output!r}")

    try:
        computed = json.loads(raw_output)
    except Exception:
        # Fallback: compute locally if sandbox output is unparseable
        computed = {
            key: {
                "change": round(m.last - m.first, 4),
                "pct": round((m.last - m.first) / m.first * 100, 2) if m.first else 0,
            }
            for key, m in body.metrics.items()
        }

    trends = {
        key: {
            **vals,
            "direction": "up" if vals["change"] > 0 else ("down" if vals["change"] < 0 else "flat"),
        }
        for key, vals in computed.items()
    }

    return {"trends": trends}
