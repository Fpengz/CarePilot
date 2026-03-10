"""Dependency wiring for API runtime stores, agents, and orchestrators."""

from dataclasses import dataclass

from dietary_guardian.agents.emotion import EmotionAgent
from dietary_guardian.agents.recommendation import RecommendationAgent
from dietary_guardian.agents.registry import AgentRegistry, build_default_agent_registry
from dietary_guardian.application.tooling.platform_registry import build_platform_tool_registry
from dietary_guardian.config.settings import Settings, get_settings
from dietary_guardian.infrastructure.auth import InMemoryAuthStore, SessionSigner, SQLiteAuthStore
from dietary_guardian.infrastructure.cache import InMemoryCacheStore, RedisCacheStore
from dietary_guardian.infrastructure.coordination import (
    InMemoryCoordinationStore,
    RedisCoordinationStore,
)
from dietary_guardian.infrastructure.emotion import EmotionRuntimeConfig, InProcessEmotionRuntime
from dietary_guardian.infrastructure.household import SQLiteHouseholdStore
from dietary_guardian.infrastructure.persistence import (
    AppStoreBackend,
    AppStores,
    build_app_store,
    build_app_stores,
)
from dietary_guardian.infrastructure.tooling.registry import ToolRegistry
from dietary_guardian.orchestrators import WorkflowCoordinator
from dietary_guardian.runtime.memory import (
    ClinicalSnapshotMemoryService,
    EventTimelineService,
    ProfileMemoryService,
)

from .services.notifications import NotificationReadStateStore

AuthStore = InMemoryAuthStore | SQLiteAuthStore
CacheStore = InMemoryCacheStore | RedisCacheStore
CoordinationStore = InMemoryCoordinationStore | RedisCoordinationStore
HouseholdStore = SQLiteHouseholdStore


@dataclass
class AppContext:
    settings: Settings
    app_store: AppStoreBackend
    stores: AppStores
    profile_memory: ProfileMemoryService
    clinical_memory: ClinicalSnapshotMemoryService
    event_timeline: EventTimelineService
    tool_registry: ToolRegistry
    agent_registry: AgentRegistry
    coordinator: WorkflowCoordinator
    auth_store: AuthStore
    session_signer: SessionSigner
    notification_reads: NotificationReadStateStore
    cache_store: CacheStore
    coordination_store: CoordinationStore
    household_store: HouseholdStore
    emotion_agent: EmotionAgent
    recommendation_agent: RecommendationAgent


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
class RecommendationAgentDeps:
    stores: AppStores
    clinical_memory: ClinicalSnapshotMemoryService
    recommendation_agent: RecommendationAgent


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
    emotion_agent: EmotionAgent


@dataclass(frozen=True)
class AlertDeps:
    stores: AppStores
    coordinator: WorkflowCoordinator


@dataclass(frozen=True)
class ClinicalCardDeps:
    stores: AppStores


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


def _build_app_store(settings: Settings) -> AppStoreBackend:
    return build_app_store(settings)


def _build_auth_store(settings: Settings) -> AuthStore:
    if settings.auth.store_backend == "in_memory":
        return InMemoryAuthStore(settings)
    return SQLiteAuthStore(settings=settings, db_path=settings.auth.sqlite_db_path)


def _build_household_store(settings: Settings) -> HouseholdStore:
    return SQLiteHouseholdStore(settings.storage.api_sqlite_db_path)


def _build_cache_store(settings: Settings) -> CacheStore:
    if settings.storage.ephemeral_state_backend == "redis":
        return RedisCacheStore(
            redis_url=str(settings.storage.redis_url),
            namespace=settings.storage.redis_namespace,
        )
    return InMemoryCacheStore()


def _build_coordination_store(settings: Settings) -> CoordinationStore:
    if settings.storage.ephemeral_state_backend == "redis":
        return RedisCoordinationStore(
            redis_url=str(settings.storage.redis_url),
            namespace=settings.storage.redis_namespace,
        )
    return InMemoryCoordinationStore()


def build_app_context() -> AppContext:
    settings = get_settings()
    app_store = _build_app_store(settings)
    profile_memory = ProfileMemoryService()
    clinical_memory = ClinicalSnapshotMemoryService()
    event_timeline = EventTimelineService(
        repository=app_store,
        persistence_enabled=settings.workers.workflow_trace_persistence_enabled,
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
    session_signer = SessionSigner(settings.auth.session_secret)
    notification_reads = NotificationReadStateStore()
    cache_store = _build_cache_store(settings)
    coordination_store = _build_coordination_store(settings)
    household_store = _build_household_store(settings)
    emotion_runtime = InProcessEmotionRuntime(EmotionRuntimeConfig.from_settings(settings))
    emotion_agent = EmotionAgent(
        runtime=emotion_runtime,
        inference_enabled=settings.emotion.inference_enabled,
        speech_enabled=settings.emotion.speech_enabled,
        request_timeout_seconds=settings.emotion.request_timeout_seconds,
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
        emotion_agent=emotion_agent,
        recommendation_agent=RecommendationAgent(),
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
    return EmotionDeps(settings=ctx.settings, emotion_agent=ctx.emotion_agent)


def recommendation_agent_deps(ctx: AppContext) -> RecommendationAgentDeps:
    return RecommendationAgentDeps(
        stores=ctx.stores,
        clinical_memory=ctx.clinical_memory,
        recommendation_agent=ctx.recommendation_agent,
    )


def alert_deps(ctx: AppContext) -> AlertDeps:
    return AlertDeps(stores=ctx.stores, coordinator=ctx.coordinator)


def clinical_card_deps(ctx: AppContext) -> ClinicalCardDeps:
    return ClinicalCardDeps(stores=ctx.stores)
