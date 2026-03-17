"""API orchestration for recommendation-agent daily plans and interactions.

Shim: canonical logic lives in ``care_pilot.features.recommendations.recommendation_engine``.
"""

from __future__ import annotations

from care_pilot.features.recommendations.recommendation_engine import (  # noqa: F401
    get_daily_agent_for_session,
    get_substitutions_for_session,
    record_interaction_for_session,
)

__all__ = [
    "get_daily_agent_for_session",
    "get_substitutions_for_session",
    "record_interaction_for_session",
]
