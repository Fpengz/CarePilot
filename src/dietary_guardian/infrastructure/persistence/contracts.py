from __future__ import annotations

from typing import TypeAlias

from dietary_guardian.services.ports import (
    ReminderNotificationRepository as ServiceReminderNotificationRepository,
    ReminderSchedulerRepository as ServiceReminderSchedulerRepository,
)

from .sqlite_app_store import SQLiteAppStore

AppStoreBackend: TypeAlias = SQLiteAppStore
ReminderNotificationRepository = ServiceReminderNotificationRepository
ReminderSchedulerRepository = ServiceReminderSchedulerRepository
