"""
Wire API dependencies for runtime stores, agents, and orchestration.

This module assembles shared runtime services used by API route handlers,
including agent registry, persistence, and platform adapters.
"""

import os
from dataclasses import dataclass

from openai import AsyncOpenAI, OpenAI

from dietary_guardian.agent.chat import AudioAgent, ChatAgent, CodeAgent, HealthTracker, QueryRouter, SearchAgent
from dietary_guardian.agent.emotion import EmotionAgent
from dietary_guardian.agent.recommendation import RecommendationAgent
from dietary_guardian.agent.core import AgentRegistry, build_default_agent_registry
from dietary_guardian.platform.observability.tooling.platform_registry import build_platform_tool_registry
from dietary_guardian.config.app import AppSettings as Settings, get_settings
from dietary_guardian.platform.auth import InMemoryAuthStore, SessionSigner, SQLiteAuthStore
from dietary_guardian.platform.cache import (
    ClinicalSnapshotMemoryService,
    EventTimelineService,
    InMemoryCacheStore,
    ProfileMemoryService,
    RedisCacheStore,
)
from dietary_guardian.platform.persistence import (
    AppStoreBackend,
    AppStores,
    build_app_store,
    build_app_stores,
)
from dietary_guardian.platform.scheduling.coordination import (
    InMemoryCoordinationStore,
    RedisCoordinationStore,
)
from dietary_guardian.agent.emotion.config import EmotionRuntimeConfig
from dietary_guardian.agent.emotion.runtime import InProcessEmotionRuntime
from dietary_guardian.platform.persistence.household import SQLiteHouseholdStore
from dietary_guardian.platform.observability.tooling.registry import ToolRegistry
from dietary_guardian.platform.observability.workflows.coordinator import WorkflowCoordinator
from dietary_guardian.features.meals.deps import MealDeps  # noqa: F401

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
    chat_agent: ChatAgent
    chat_audio_agent: AudioAgent
    chat_async_client: AsyncOpenAI
    chat_model_id: str
    chat_health_tracker: HealthTracker
    chat_code_agent: CodeAgent


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
class ChatDeps:
    chat_agent: ChatAgent
    audio_agent: AudioAgent
    emotion_agent: EmotionAgent
    async_client: AsyncOpenAI
    model_id: str
    health_tracker: HealthTracker
    code_agent: CodeAgent


@dataclass(frozen=True)
class AlertDeps:
    stores: AppStores
    coordinator: WorkflowCoordinator


@dataclass(frozen=True)
class ClinicalCardDeps:
    stores: AppStores


@dataclass(frozen=True)
class AuthContext:
    """Focused context for session validation — auth routes only."""

    auth_store: AuthStore
    session_signer: SessionSigner
    settings: Settings


def auth_context(ctx: AppContext) -> AuthContext:
    """Extract the auth-focused context slice from AppContext."""
    return AuthContext(
        auth_store=ctx.auth_store,
        session_signer=ctx.session_signer,
        settings=ctx.settings,
    )


def close_app_context(ctx: AppContext) -> None:
    for component in (
        ctx.app_store,
        ctx.auth_store,
        ctx.household_store,
        ctx.cache_store,
        ctx.coordination_store,
        ctx.chat_async_client,
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
    chat_model_id = os.environ.get("CHAT_MODEL_ID", "aisingapore/Gemma-SEA-LION-v4-27B-IT")
    chat_reasoning_model_id = os.environ.get("REASONING_MODEL_ID", "aisingapore/Llama-SEA-LION-v3.5-70B-R")
    chat_base_url = os.environ.get("SEALION_BASE_URL", "https://api.sea-lion.ai/v1")
    chat_api_key = os.environ.get("SEALION_API") or settings.llm.openai.api_key or ""
    chat_search_agent = SearchAgent(max_results=3)
    chat_client = OpenAI(api_key=chat_api_key, base_url=chat_base_url)
    chat_code_agent = CodeAgent(api_key=os.environ.get("E2B_API_KEY"))
    chat_router = QueryRouter(
        search_agent=chat_search_agent,
        client=chat_client,
        model_id=chat_model_id,
        code_agent=chat_code_agent,
        reasoning_model_id=chat_reasoning_model_id,
    )
    chat_agent = ChatAgent(
        client=chat_client,
        model_id=chat_model_id,
        router=chat_router,
    )
    chat_audio_agent = AudioAgent(
        repo_id=os.environ.get("TRANSCRIPTION_MODEL_ID"),
        groq_api_key=os.environ.get("GROQ_API_KEY"),
    )
    chat_async_client = AsyncOpenAI(api_key=chat_api_key, base_url=chat_base_url)
    chat_health_tracker = HealthTracker(
        session_id="default",
        client=chat_client,
        model_id=chat_model_id,
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
        chat_agent=chat_agent,
        chat_audio_agent=chat_audio_agent,
        chat_async_client=chat_async_client,
        chat_model_id=chat_model_id,
        chat_health_tracker=chat_health_tracker,
        chat_code_agent=chat_code_agent,
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


def chat_deps(ctx: AppContext) -> ChatDeps:
    return ChatDeps(
        chat_agent=ctx.chat_agent,
        audio_agent=ctx.chat_audio_agent,
        emotion_agent=ctx.emotion_agent,
        async_client=ctx.chat_async_client,
        model_id=ctx.chat_model_id,
        health_tracker=ctx.chat_health_tracker,
        code_agent=ctx.chat_code_agent,
    )


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
