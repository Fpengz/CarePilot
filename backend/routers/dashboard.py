"""
backend/routers/dashboard.py
-----------------------------
Endpoints:
    GET /api/dashboard/entries?start=YYYY-MM-DD&end=YYYY-MM-DD
        — raw [TRACK] messages in the date range

    GET /api/dashboard/chart-data?start=YYYY-MM-DD&end=YYYY-MM-DD
        — parsed & grouped metric data ready for Recharts
"""
from fastapi import APIRouter, Query

from backend.deps import health_tracker

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


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
