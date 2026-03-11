"""Canonical safety service entrypoint."""

from dietary_guardian.features.safety.use_cases import apply_safety_decision, review_care_plan

__all__ = ["apply_safety_decision", "review_care_plan"]
