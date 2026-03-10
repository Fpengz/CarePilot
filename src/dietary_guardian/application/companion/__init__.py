"""Package exports for companion: snapshot, engagement, care plan, digest, impact, personalization, and interaction orchestration."""

from .care_plan import compose_care_plan
from .digest import build_clinician_digest
from .engagement import assess_engagement
from .impact import build_impact_summary
from .personalization import (
    build_caregiver_tool_state,
    build_clinical_summary_tool_state,
    build_personalization_context,
    build_self_tool_state,
    get_profile_sections,
)
from .snapshot import build_case_snapshot
from .use_cases import (
    CompanionStateInputs,
    build_companion_runtime_state,
    build_companion_today_bundle,
    run_companion_interaction,
)
__all__ = [
    "build_case_snapshot",
    "assess_engagement",
    "compose_care_plan",
    "build_clinician_digest",
    "build_impact_summary",
    "build_personalization_context",
    "build_caregiver_tool_state",
    "build_clinical_summary_tool_state",
    "build_self_tool_state",
    "get_profile_sections",
    "CompanionStateInputs",
    "build_companion_runtime_state",
    "build_companion_today_bundle",
    "run_companion_interaction",
]
