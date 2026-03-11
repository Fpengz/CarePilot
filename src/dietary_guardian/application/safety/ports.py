"""Port definition for clinical safety validation — implemented by SafetyEngine."""

from __future__ import annotations

from typing import Protocol

from dietary_guardian.domain.meals.models import MealEvent


class SafetyPort(Protocol):
    """Validates a meal against clinical safety rules for a given user."""

    def validate_meal(self, meal: MealEvent) -> list[str]:
        """Return warning strings. Raise SafetyViolation for critical violations."""
        ...
