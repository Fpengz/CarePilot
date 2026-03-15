"""
Define safety domain ports.

This module declares interfaces used by safety workflows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from care_pilot.features.meals.domain.models import MealEvent


class DrugInteractionRepository(Protocol):
    """Protocol for drug/food interaction database lookups."""

    def get_contraindications(self, medication_name: str) -> list[tuple[str, str, str]]: ...


class SafetyPort(Protocol):
    """Validates a meal against clinical safety rules for a given user."""

    def validate_meal(self, meal: "MealEvent") -> list[str]:
        """Return warning strings. Raise SafetyViolation for critical violations."""
        ...
