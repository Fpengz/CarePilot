"""API orchestration for report-driven and session-scoped suggestions.

Re-exports from :mod:`dietary_guardian.application.recommendations.suggestion_session`.
"""

from dietary_guardian.application.recommendations.suggestion_session import generate_from_report  # noqa: F401
from dietary_guardian.application.recommendations.suggestion_session import get_for_session  # noqa: F401
from dietary_guardian.application.recommendations.suggestion_session import list_for_session  # noqa: F401

__all__ = ["generate_from_report", "get_for_session", "list_for_session"]
