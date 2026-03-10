"""Package exports for recommendations."""

from .use_cases import (
    MissingActiveHouseholdError,
    NoMealRecordsError,
    SuggestionForbiddenError,
    SuggestionNotFoundError,
    generate_recommendation_for_session,
    generate_suggestion_from_report,
    get_daily_agent_for_session,
    get_substitutions_for_session,
    get_suggestion_for_session,
    list_suggestions_for_session,
    record_interaction_for_session,
)

__all__ = [
    "MissingActiveHouseholdError",
    "NoMealRecordsError",
    "SuggestionForbiddenError",
    "SuggestionNotFoundError",
    "generate_recommendation_for_session",
    "generate_suggestion_from_report",
    "get_daily_agent_for_session",
    "get_substitutions_for_session",
    "get_suggestion_for_session",
    "list_suggestions_for_session",
    "record_interaction_for_session",
]
