"""
Define dependencies for meal use cases.

This module hosts dependency type hints used by the meals feature.
"""

from __future__ import annotations

from dataclasses import dataclass

from care_pilot.config.app import AppSettings as Settings
from care_pilot.platform.cache import EventTimelineService
from care_pilot.platform.memory import MemoryStore
from care_pilot.platform.persistence import AppStores


@dataclass(frozen=True)
class MealDeps:
    settings: Settings
    stores: AppStores
    event_timeline: EventTimelineService
    memory_store: MemoryStore
