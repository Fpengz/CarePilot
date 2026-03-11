"""Port protocol for drug interaction lookup — keeps domain free of infrastructure."""

from __future__ import annotations

from typing import Protocol


class DrugInteractionRepository(Protocol):
    """Protocol for drug/food interaction database lookups."""

    def get_contraindications(self, medication_name: str) -> list[tuple[str, str, str]]: ...
