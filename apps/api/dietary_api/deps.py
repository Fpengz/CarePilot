from dataclasses import dataclass
from typing import Any

from dietary_guardian.config.settings import Settings, get_settings
from dietary_guardian.infrastructure.auth import InMemoryAuthStore, PostgresAuthStore, SQLiteAuthStore, SessionSigner
from dietary_guardian.infrastructure.cache import InMemoryCacheStore, RedisCacheStore
from dietary_guardian.infrastructure.coordination import InMemoryCoordinationStore, RedisCoordinationStore
from dietary_guardian.infrastructure.emotion import EmotionRuntimeConfig, InProcessEmotionRuntime
from dietary_guardian.infrastructure.household import PostgresHouseholdStore, SQLiteHouseholdStore
from dietary_guardian.infrastructure.persistence import AppStores, PostgresAppStore, SQLiteAppStore, build_app_stores
from dietary_guardian.services.emotion_service import EmotionService
from dietary_guardian.services.memory_services import (
    ClinicalSnapshotMemoryService,
    EventTimelineService,
    ProfileMemoryService,
)
from dietary_guardian.services.agent_registry import AgentRegistry, build_default_agent_registry
from dietary_guardian.services.platform_tools import build_platform_tool_registry
from dietary_guardian.services.workflow_coordinator import WorkflowCoordinator

from .services.notifications import NotificationReadStateStore


@dataclass
class AppContext:
    settings: Settings
    app_store: Any
    stores: AppStores
    profile_memory: ProfileMemoryService
    clinical_memory: ClinicalSnapshotMemoryService
    event_timeline: EventTimelineService
    tool_registry: Any
    agent_registry: AgentRegistry
    coordinator: WorkflowCoordinator
    auth_store: Any
    session_signer: SessionSigner
    notification_reads: NotificationReadStateStore
    cache_store: Any
    coordination_store: Any
    household_store: Any
    emotion_service: EmotionService


@dataclass(frozen=True)
class MealDeps:
    settings: Settings
    stores: AppStores
    coordinator: WorkflowCoordinator


@dataclass(frozen=True)
class RecommendationDeps:
    stores: AppStores
    clinical_memory: ClinicalSnapshotMemoryService


@dataclass(frozen=True)
class WorkflowDeps:
    settings: Settings
    stores: AppStores
    event_timeline: EventTimelineService
    agent_registry: AgentRegistry
    coordinator: WorkflowCoordinator


@dataclass(frozen=True)
class EmotionDeps:
    settings: Settings
    emotion_service: EmotionService


def close_app_context(ctx: AppContext) -> None:
    for component in (
        ctx.app_store,
        ctx.auth_store,
        ctx.household_store,
        ctx.cache_store,
        ctx.coordination_store,
    ):
        close = getattr(component, "close", None)
        if callable(close):
            close()


def _build_app_store(settings: Settings) -> Any:
    if settings.app_data_backend == "sqlite":
        return SQLiteAppStore(settings.api_sqlite_db_path)
    return PostgresAppStore(dsn=str(settings.postgres_dsn))


def _build_auth_store(settings: Settings) -> Any:
    if settings.auth_store_backend == "sqlite":
        return SQLiteAuthStore(settings=settings, db_path=settings.auth_sqlite_db_path)
    if settings.auth_store_backend == "in_memory":
        return InMemoryAuthStore(settings)
    return PostgresAuthStore(settings=settings, dsn=str(settings.postgres_dsn))


def _build_household_store(settings: Settings) -> Any:
    if settings.household_store_backend == "sqlite":
        return SQLiteHouseholdStore(settings.api_sqlite_db_path)
    return PostgresHouseholdStore(dsn=str(settings.postgres_dsn))


def _build_cache_store(settings: Settings) -> Any:
    if settings.ephemeral_state_backend == "redis":
        return RedisCacheStore(
            redis_url=str(settings.redis_url),
            namespace=settings.redis_namespace,
            keyspace_version=settings.redis_keyspace_version,
        )
    return InMemoryCacheStore()


def _build_coordination_store(settings: Settings) -> Any:
    if settings.ephemeral_state_backend == "redis":
        return RedisCoordinationStore(
            redis_url=str(settings.redis_url),
            namespace=settings.redis_namespace,
            keyspace_version=settings.redis_keyspace_version,
        )
    return InMemoryCoordinationStore()


def build_app_context() -> AppContext:
    settings = get_settings()
    app_store = _build_app_store(settings)
    profile_memory = ProfileMemoryService()
    clinical_memory = ClinicalSnapshotMemoryService()
    event_timeline = EventTimelineService(
        repository=app_store,
        persistence_enabled=settings.workflow_trace_persistence_enabled,
    )
    tool_registry = build_platform_tool_registry(app_store)
    agent_registry = build_default_agent_registry()
    coordinator = WorkflowCoordinator(
        tool_registry=tool_registry,
        profile_memory=profile_memory,
        clinical_memory=clinical_memory,
        event_timeline=event_timeline,
    )
    auth_store = _build_auth_store(settings)
    session_signer = SessionSigner(settings.session_secret)
    notification_reads = NotificationReadStateStore()
    cache_store = _build_cache_store(settings)
    coordination_store = _build_coordination_store(settings)
    household_store = _build_household_store(settings)
    emotion_runtime = InProcessEmotionRuntime(EmotionRuntimeConfig.from_settings(settings))
    emotion_service = EmotionService(
        runtime=emotion_runtime,
        inference_enabled=settings.emotion_inference_enabled,
        speech_enabled=settings.emotion_speech_enabled,
        request_timeout_seconds=settings.emotion_request_timeout_seconds,
    )
    ctx = AppContext(
        settings=settings,
        app_store=app_store,
        stores=build_app_stores(app_store),
        profile_memory=profile_memory,
        clinical_memory=clinical_memory,
        event_timeline=event_timeline,
        tool_registry=tool_registry,
        agent_registry=agent_registry,
        coordinator=coordinator,
        auth_store=auth_store,
        session_signer=session_signer,
        notification_reads=notification_reads,
        cache_store=cache_store,
        coordination_store=coordination_store,
        household_store=household_store,
        emotion_service=emotion_service,
    )
    from .services.workflows import ensure_runtime_contract_snapshot_bootstrap

    ensure_runtime_contract_snapshot_bootstrap(context=ctx)
    return ctx


def meal_deps(ctx: AppContext) -> MealDeps:
    return MealDeps(settings=ctx.settings, stores=ctx.stores, coordinator=ctx.coordinator)


def recommendation_deps(ctx: AppContext) -> RecommendationDeps:
    return RecommendationDeps(stores=ctx.stores, clinical_memory=ctx.clinical_memory)


def workflow_deps(ctx: AppContext) -> WorkflowDeps:
    return WorkflowDeps(
        settings=ctx.settings,
        stores=ctx.stores,
        event_timeline=ctx.event_timeline,
        agent_registry=ctx.agent_registry,
        coordinator=ctx.coordinator,
    )


def emotion_deps(ctx: AppContext) -> EmotionDeps:
    return EmotionDeps(settings=ctx.settings, emotion_service=ctx.emotion_service)
