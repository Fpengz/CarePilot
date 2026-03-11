"""API orchestration for recommendation-agent daily plans and interactions.

Shim: canonical logic lives in ``dietary_guardian.features.recommendations.service``.
"""

from __future__ import annotations

from dietary_guardian.features.recommendations.service import (  # noqa: F401
    get_daily_agent_for_session,
    get_substitutions_for_session,
    record_interaction_for_session,
)

__all__ = [
    "get_daily_agent_for_session",
    "get_substitutions_for_session",
    "record_interaction_for_session",
]
