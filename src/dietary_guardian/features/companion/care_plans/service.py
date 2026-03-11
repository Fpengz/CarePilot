"""Canonical companion care-plan service entrypoint."""

from dietary_guardian.features.companion.care_plans.care_plan import compose_care_plan

__all__ = ["compose_care_plan"]
