from __future__ import annotations

from typing import TypeAlias

from dietary_guardian.application.contracts.notifications import (
    ReminderNotificationRepository as ServiceReminderNotificationRepository,
)
from dietary_guardian.application.contracts.notifications import (
    ReminderSchedulerRepository as ServiceReminderSchedulerRepository,
)

from .sqlite_app_store import SQLiteAppStore

AppStoreBackend: TypeAlias = SQLiteAppStore
ReminderNotificationRepository = ServiceReminderNotificationRepository
ReminderSchedulerRepository = ServiceReminderSchedulerRepository
