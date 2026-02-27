from dataclasses import dataclass
from typing import Any

from dietary_guardian.config.settings import Settings, get_settings
from dietary_guardian.services.memory_services import (
    ClinicalSnapshotMemoryService,
    EventTimelineService,
    ProfileMemoryService,
)
from dietary_guardian.services.platform_tools import build_platform_tool_registry
from dietary_guardian.services.repository import SQLiteRepository
from dietary_guardian.services.workflow_coordinator import WorkflowCoordinator

from .auth import SessionSigner
from dietary_guardian.infrastructure.auth import InMemoryAuthStore, SQLiteAuthStore
from dietary_guardian.infrastructure.household import SQLiteHouseholdStore
from .services.notifications import NotificationReadStateStore


@dataclass
class AppContext:
    settings: Settings
    repository: SQLiteRepository
    profile_memory: ProfileMemoryService
    clinical_memory: ClinicalSnapshotMemoryService
    event_timeline: EventTimelineService
    tool_registry: Any
    coordinator: WorkflowCoordinator
    auth_store: Any
    session_signer: SessionSigner
    notification_reads: NotificationReadStateStore
    household_store: Any


def close_app_context(ctx: AppContext) -> None:
    for component in (ctx.repository, ctx.auth_store, ctx.household_store):
        close = getattr(component, "close", None)
        if callable(close):
            close()


def build_app_context() -> AppContext:
    settings = get_settings()
    repository = SQLiteRepository(settings.api_sqlite_db_path)
    profile_memory = ProfileMemoryService()
    clinical_memory = ClinicalSnapshotMemoryService()
    event_timeline = EventTimelineService()
    tool_registry = build_platform_tool_registry(repository)
    coordinator = WorkflowCoordinator(
        tool_registry=tool_registry,
        profile_memory=profile_memory,
        clinical_memory=clinical_memory,
        event_timeline=event_timeline,
    )
    auth_store = (
        SQLiteAuthStore(settings=settings, db_path=settings.auth_sqlite_db_path)
        if settings.auth_store_backend == "sqlite"
        else InMemoryAuthStore(settings)
    )
    session_signer = SessionSigner(settings.session_secret)
    notification_reads = NotificationReadStateStore()
    household_store = SQLiteHouseholdStore(settings.api_sqlite_db_path)
    return AppContext(
        settings=settings,
        repository=repository,
        profile_memory=profile_memory,
        clinical_memory=clinical_memory,
        event_timeline=event_timeline,
        tool_registry=tool_registry,
        coordinator=coordinator,
        auth_store=auth_store,
        session_signer=session_signer,
        notification_reads=notification_reads,
        household_store=household_store,
    )
