"""Canonical persistence platform exports."""

from dietary_guardian.platform.persistence.builders import build_app_store
from dietary_guardian.platform.persistence.contracts import (
    AppStoreBackend,
    ReminderNotificationRepository,
    ReminderSchedulerRepository,
)
from dietary_guardian.platform.persistence.domain_stores import AppStores, build_app_stores
from dietary_guardian.platform.persistence.protocols import (
    AlertRepositoryProtocol,
    CatalogRepositoryProtocol,
    ClinicalCardRepositoryProtocol,
    ClinicalRepositoryProtocol,
    FoodRepositoryProtocol,
    MealRepositoryProtocol,
    MedicationRepositoryProtocol,
    ProfileRepositoryProtocol,
    ReminderRepositoryProtocol,
    WorkflowRepositoryProtocol,
)
from dietary_guardian.platform.persistence.runtime_bootstrap import (
    build_alert_repository,
    build_reminder_notification_repository,
    build_reminder_scheduler_repository,
    build_runtime_store,
)
from dietary_guardian.platform.persistence.sqlite_app_store import SQLiteAppStore
from dietary_guardian.platform.persistence.sqlite_repository import SQLiteRepository

__all__ = [
    "AlertRepositoryProtocol",
    "AppStoreBackend",
    "AppStores",
    "CatalogRepositoryProtocol",
    "ClinicalCardRepositoryProtocol",
    "ClinicalRepositoryProtocol",
    "FoodRepositoryProtocol",
    "MealRepositoryProtocol",
    "MedicationRepositoryProtocol",
    "ProfileRepositoryProtocol",
    "ReminderNotificationRepository",
    "ReminderRepositoryProtocol",
    "ReminderSchedulerRepository",
    "SQLiteAppStore",
    "SQLiteRepository",
    "WorkflowRepositoryProtocol",
    "build_alert_repository",
    "build_app_store",
    "build_app_stores",
    "build_reminder_notification_repository",
    "build_reminder_scheduler_repository",
    "build_runtime_store",
]
