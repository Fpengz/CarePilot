"""API helper for single recommendation generation flows.

Shim: canonical logic lives in ``care_pilot.features.recommendations.recommendation_engine``.
"""

from __future__ import annotations

from care_pilot.features.recommendations.recommendation_engine import (  # noqa: F401
    generate_recommendation_for_session,
)

__all__ = ["generate_recommendation_for_session"]
