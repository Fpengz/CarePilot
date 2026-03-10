"""Backward-compatible re-export shim.

The recommendation scoring engine has moved to
``dietary_guardian.domain.recommendations.engine``.
"""

from dietary_guardian.domain.recommendations.engine import (  # noqa: F401
    AgentMealNotFoundError,
    build_substitution_plan,
    generate_daily_agent_recommendation,
    record_interaction_and_update_preferences,
)

__all__ = [
    "AgentMealNotFoundError",
    "build_substitution_plan",
    "generate_daily_agent_recommendation",
    "record_interaction_and_update_preferences",
]
