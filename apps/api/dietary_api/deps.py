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

from .auth import InMemoryAuthStore, SessionSigner


@dataclass
class AppContext:
    settings: Settings
    repository: SQLiteRepository
    profile_memory: ProfileMemoryService
    clinical_memory: ClinicalSnapshotMemoryService
    event_timeline: EventTimelineService
    tool_registry: Any
    coordinator: WorkflowCoordinator
    auth_store: InMemoryAuthStore
    session_signer: SessionSigner


def build_app_context() -> AppContext:
    settings = get_settings()
    repository = SQLiteRepository("dietary_guardian_api.db")
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
    auth_store = InMemoryAuthStore(settings)
    session_signer = SessionSigner(settings.session_secret)
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
    )

