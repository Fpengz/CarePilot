"""
Define persistence contract primitives.

This module contains shared types for persistence adapters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from care_pilot.core.contracts.notifications import (
    MessageNotificationRepository as ServiceMessageNotificationRepository,
    ReminderSchedulerRepository as ServiceReminderSchedulerRepository,
)

if TYPE_CHECKING:
    from .builders import SQLiteAppStore

if TYPE_CHECKING:
    type AppStoreBackend = SQLiteAppStore
else:
    type AppStoreBackend = Any
MessageNotificationRepository = ServiceMessageNotificationRepository
ReminderSchedulerRepository = ServiceReminderSchedulerRepository
