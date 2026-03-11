"""Canonical recommendations service entrypoint."""

from dietary_guardian.features.recommendations.suggestion_session import (
    generate_from_report,
    get_for_session,
    list_for_session,
)
from dietary_guardian.features.recommendations.use_cases import (
    generate_recommendation_for_session,
    generate_suggestion_from_report,
    get_daily_agent_for_session,
    get_substitutions_for_session,
    get_suggestion_for_session,
    list_suggestions_for_session,
    record_interaction_for_session,
)

__all__ = [
    "generate_from_report",
    "generate_recommendation_for_session",
    "generate_suggestion_from_report",
    "get_daily_agent_for_session",
    "get_for_session",
    "get_substitutions_for_session",
    "get_suggestion_for_session",
    "list_for_session",
    "list_suggestions_for_session",
    "record_interaction_for_session",
]
