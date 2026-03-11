"""Infrastructure support for contracts."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

from dietary_guardian.core.contracts.notifications import (
    ReminderNotificationRepository as ServiceReminderNotificationRepository,
)
from dietary_guardian.core.contracts.notifications import (
    ReminderSchedulerRepository as ServiceReminderSchedulerRepository,
)

if TYPE_CHECKING:
    from .sqlite_app_store import SQLiteAppStore

AppStoreBackend: TypeAlias = "SQLiteAppStore"
ReminderNotificationRepository = ServiceReminderNotificationRepository
ReminderSchedulerRepository = ServiceReminderSchedulerRepository
