"""API helpers for lightweight metric-trend reads.

Re-exports from :mod:`dietary_guardian.features.companion.impact.metrics.use_cases`.
"""

from dietary_guardian.features.companion.impact.metrics.use_cases import list_metric_trends_for_session  # noqa: F401

__all__ = ["list_metric_trends_for_session"]
