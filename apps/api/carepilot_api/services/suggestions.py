"""API orchestration for report-driven and session-scoped suggestions.

Re-exports from :mod:`care_pilot.features.recommendations.service`.
"""

from care_pilot.features.recommendations.service import (
    generate_from_report,
)  # noqa: F401
from care_pilot.features.recommendations.service import (
    get_for_session,
)  # noqa: F401
from care_pilot.features.recommendations.service import (
    list_for_session,
)  # noqa: F401

__all__ = ["generate_from_report", "get_for_session", "list_for_session"]
