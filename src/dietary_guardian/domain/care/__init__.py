"""Backward-compatible re-export shim.

The companion domain models have moved to
``dietary_guardian.domain.companion``.
"""

from dietary_guardian.domain.companion import (  # noqa: F401
    CarePlan,
    CaseSnapshot,
    ClinicianDigest,
    CompanionInteraction,
    CompanionInteractionResult,
    EngagementAssessment,
    ImpactSummary,
    PersonalizationContext,
)

__all__ = [
    "CarePlan",
    "CaseSnapshot",
    "ClinicianDigest",
    "CompanionInteraction",
    "CompanionInteractionResult",
    "EngagementAssessment",
    "ImpactSummary",
    "PersonalizationContext",
]
