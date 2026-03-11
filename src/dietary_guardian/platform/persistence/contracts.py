"""Infrastructure support for contracts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeAlias

from dietary_guardian.core.contracts.notifications import (
    ReminderNotificationRepository as ServiceReminderNotificationRepository,
)
from dietary_guardian.core.contracts.notifications import (
    ReminderSchedulerRepository as ServiceReminderSchedulerRepository,
)

if TYPE_CHECKING:
    from .sqlite_app_store import SQLiteAppStore

if TYPE_CHECKING:
    AppStoreBackend: TypeAlias = SQLiteAppStore
else:
    AppStoreBackend: TypeAlias = Any
ReminderNotificationRepository = ServiceReminderNotificationRepository
ReminderSchedulerRepository = ServiceReminderSchedulerRepository
