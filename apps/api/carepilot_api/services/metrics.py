"""API helpers for lightweight metric-trend reads.

Re-exports from :mod:`care_pilot.features.companion.impact.metrics.impact_metric_service`.
"""

from care_pilot.features.companion.impact.metrics.impact_metric_service import (
    list_metric_trends_for_session,
)  # noqa: F401

__all__ = ["list_metric_trends_for_session"]
