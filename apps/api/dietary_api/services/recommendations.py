"""API helper for single recommendation generation flows.

Shim: business logic lives in dietary_guardian.application.recommendations.use_cases.
"""

from __future__ import annotations

from dietary_guardian.application.recommendations.use_cases import (  # noqa: F401
    generate_recommendation_for_session,
)

__all__ = ["generate_recommendation_for_session"]
