"""API helper for single recommendation generation flows.

Shim: canonical logic lives in ``dietary_guardian.features.recommendations.service``.
"""

from __future__ import annotations

from dietary_guardian.features.recommendations.service import (  # noqa: F401
    generate_recommendation_for_session,
)

__all__ = ["generate_recommendation_for_session"]
