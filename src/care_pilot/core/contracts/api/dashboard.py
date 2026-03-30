"""Dashboard API contracts."""

from __future__ import annotations

from typing import Literal

# Dashboard primitives
DashboardBucket = Literal["hour", "day", "week"]

__all__ = ["DashboardBucket"]
