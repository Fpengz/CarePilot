"""
Define persistence contract primitives.

This module contains shared types for persistence adapters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from care_pilot.core.contracts.notifications import (
    ReminderNotificationRepository as ServiceReminderNotificationRepository,
)
from care_pilot.core.contracts.notifications import (
    ReminderSchedulerRepository as ServiceReminderSchedulerRepository,
)

if TYPE_CHECKING:
    from .sqlite_app_store import SQLiteAppStore

if TYPE_CHECKING:
    type AppStoreBackend = SQLiteAppStore
else:
    type AppStoreBackend = Any
ReminderNotificationRepository = ServiceReminderNotificationRepository
ReminderSchedulerRepository = ServiceReminderSchedulerRepository
