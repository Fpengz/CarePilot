"""API orchestration for recommendation-agent daily plans and interactions.

Shim: business logic lives in dietary_guardian.application.recommendations.use_cases.
"""

from __future__ import annotations

from dietary_guardian.application.recommendations.use_cases import (  # noqa: F401
    get_daily_agent_for_session,
    get_substitutions_for_session,
    record_interaction_for_session,
)

__all__ = [
    "get_daily_agent_for_session",
    "get_substitutions_for_session",
    "record_interaction_for_session",
]
