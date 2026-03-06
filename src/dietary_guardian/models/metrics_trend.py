from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MetricPoint(BaseModel):
    timestamp: datetime
    value: float


class MetricTrend(BaseModel):
    metric: str
    points: list[MetricPoint] = Field(default_factory=list)
    delta: float = 0.0
    percent_change: float | None = None
    slope_per_point: float = 0.0
    direction: Literal["increase", "decrease", "flat"] = "flat"
