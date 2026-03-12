"""
Define dependencies for meal use cases.

This module hosts dependency type hints used by the meals feature.
"""

from __future__ import annotations

from dataclasses import dataclass

from dietary_guardian.config.app import AppSettings as Settings
from dietary_guardian.platform.observability.workflows.coordinator import WorkflowCoordinator
from dietary_guardian.platform.persistence import AppStores


@dataclass(frozen=True)
class MealDeps:
    settings: Settings
    stores: AppStores
    coordinator: WorkflowCoordinator
