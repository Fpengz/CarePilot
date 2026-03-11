"""API orchestration for report-driven and session-scoped suggestions.

Re-exports from :mod:`dietary_guardian.features.recommendations.service`.
"""

from dietary_guardian.features.recommendations.service import generate_from_report  # noqa: F401
from dietary_guardian.features.recommendations.service import get_for_session  # noqa: F401
from dietary_guardian.features.recommendations.service import list_for_session  # noqa: F401

__all__ = ["generate_from_report", "get_for_session", "list_for_session"]
