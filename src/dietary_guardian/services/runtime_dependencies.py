from __future__ import annotations

from typing import cast

from dietary_guardian.config.settings import Settings, get_settings
from dietary_guardian.infrastructure.persistence import AppStoreBackend, build_app_store
from dietary_guardian.services.alerting_service import AlertRepositoryProtocol
from dietary_guardian.services.ports import ReminderNotificationRepository, ReminderSchedulerRepository


def build_runtime_store(settings: Settings | None = None) -> AppStoreBackend:
    return build_app_store(settings or get_settings())


def build_reminder_scheduler_repository(settings: Settings | None = None) -> ReminderSchedulerRepository:
    return cast(ReminderSchedulerRepository, build_runtime_store(settings))


def build_reminder_notification_repository(settings: Settings | None = None) -> ReminderNotificationRepository:
    return cast(ReminderNotificationRepository, build_runtime_store(settings))


def build_alert_repository(settings: Settings | None = None) -> AlertRepositoryProtocol:
    return cast(AlertRepositoryProtocol, build_runtime_store(settings))
