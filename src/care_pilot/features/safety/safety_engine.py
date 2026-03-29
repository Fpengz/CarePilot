"""
Provide the safety service entrypoint.

This module exposes safety evaluation workflows to callers.
"""

from care_pilot.features.safety.safety_service import apply_safety_decision, review_care_plan

__all__ = ["apply_safety_decision", "review_care_plan"]
