"""
Wire API dependencies for runtime stores, agents, and orchestration.

This module assembles shared runtime services used by API route handlers,
including agent registry, persistence, and platform adapters.
"""

import os
from dataclasses import dataclass

from dietary_guardian.features.companion.chat.memory import MemoryManager
from dietary_guardian.features.companion.chat.router import QueryRouter
from dietary_guardian.features.companion.chat.orchestrator import ChatOrchestrator
from dietary_guardian.features.companion.chat.audio_adapter import AudioAgent
from dietary_guardian.features.companion.chat.code_adapter import CodeAgent
from dietary_guardian.features.companion.chat.search_adapter import SearchAgent
from dietary_guardian.features.companion.chat.health_tracker import HealthTracker
from dietary_guardian.agent.emotion.agent import EmotionAgent
from dietary_guardian.agent.emotion.schemas import EmotionInferenceResult, EmotionRuntimeHealth
from dietary_guardian.agent.recommendation.agent import RecommendationAgent
from dietary_guardian.agent.core import AgentRegistry, build_default_agent_registry
from dietary_guardian.agent.runtime.inference_engine import InferenceEngine
from dietary_guardian.agent.runtime.chat_runtime import (
    ChatRuntimeConfig,
    ChatStreamRuntime,
    build_chat_inference_engine,
    build_chat_runtime_config,
)
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
from dietary_guardian.features.companion.emotion.config import EmotionRuntimeConfig
from dietary_guardian.features.companion.emotion.runtime import InProcessEmotionRuntime
from dietary_guardian.platform.persistence.household import SQLiteHouseholdStore
from dietary_guardian.platform.observability.tooling.registry import ToolRegistry
from dietary_guardian.features.meals.deps import MealDeps  # noqa: F401
from dietary_guardian.platform.memory import MemoryStore, build_memory_store

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
    auth_store: AuthStore
    session_signer: SessionSigner
    memory_store: MemoryStore
    notification_reads: NotificationReadStateStore
    cache_store: CacheStore
    coordination_store: CoordinationStore
    household_store: HouseholdStore
    emotion_agent: EmotionAgent
    recommendation_agent: RecommendationAgent
    chat_inference_engine: InferenceEngine
    chat_router: QueryRouter
    chat_runtime_config: ChatRuntimeConfig
    chat_stream_runtime: ChatStreamRuntime
    chat_audio_agent: AudioAgent
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


@dataclass(frozen=True)
class EmotionDeps:
    settings: Settings
    emotion_agent: EmotionAgent
    event_timeline: EventTimelineService


@dataclass(frozen=True)
class ChatDeps:
    chat_agent: ChatOrchestrator
    audio_agent: AudioAgent
    emotion_agent: EmotionAgent
    health_tracker: HealthTracker
    code_agent: CodeAgent
    event_timeline: EventTimelineService


@dataclass(frozen=True)
class AlertDeps:
    stores: AppStores
    tool_registry: ToolRegistry
    event_timeline: EventTimelineService


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
    auth_store = _build_auth_store(settings)
    memory_store = build_memory_store(settings)
    session_signer = SessionSigner(settings.auth.session_secret)
    notification_reads = NotificationReadStateStore()
    cache_store = _build_cache_store(settings)
    coordination_store = _build_coordination_store(settings)
    household_store = _build_household_store(settings)
    if settings.emotion.inference_enabled or settings.emotion.speech_enabled:
        emotion_runtime = InProcessEmotionRuntime(EmotionRuntimeConfig.from_settings(settings))
    else:
        class _DisabledEmotionRuntime:
            def infer_text(self, payload) -> EmotionInferenceResult:  # noqa: ANN001
                del payload
                raise RuntimeError("emotion runtime disabled")

            def infer_speech(self, payload) -> EmotionInferenceResult:  # noqa: ANN001
                del payload
                raise RuntimeError("emotion runtime disabled")

            def health(self) -> EmotionRuntimeHealth:
                return EmotionRuntimeHealth(
                    status="disabled",
                    model_cache_ready=False,
                    source_commit=settings.emotion.source_commit,
                    detail="emotion inference disabled",
                )

        emotion_runtime = _DisabledEmotionRuntime()
    emotion_agent = EmotionAgent(
        runtime=emotion_runtime,
        inference_enabled=settings.emotion.inference_enabled,
        speech_enabled=settings.emotion.speech_enabled,
        request_timeout_seconds=settings.emotion.request_timeout_seconds,
    )
    chat_runtime_config = build_chat_runtime_config(settings)
    chat_search_agent = SearchAgent(max_results=3)
    chat_code_agent = CodeAgent(api_key=os.environ.get("E2B_API_KEY"))
    chat_inference_engine = build_chat_inference_engine(settings, model_id=chat_runtime_config.model_id)
    chat_reasoning_engine = build_chat_inference_engine(settings, model_id=chat_runtime_config.reasoning_model_id)
    chat_router = QueryRouter(
        search_agent=chat_search_agent,
        inference_engine=chat_inference_engine,
        code_agent=chat_code_agent,
        reasoning_engine=chat_reasoning_engine,
    )
    chat_stream_runtime = ChatStreamRuntime(settings)
    chat_audio_agent = AudioAgent(
        repo_id=os.environ.get("TRANSCRIPTION_MODEL_ID"),
        groq_api_key=os.environ.get("GROQ_API_KEY"),
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
        auth_store=auth_store,
        session_signer=session_signer,
        memory_store=memory_store,
        notification_reads=notification_reads,
        cache_store=cache_store,
        coordination_store=coordination_store,
        household_store=household_store,
        emotion_agent=emotion_agent,
        recommendation_agent=RecommendationAgent(),
        chat_inference_engine=chat_inference_engine,
        chat_router=chat_router,
        chat_runtime_config=chat_runtime_config,
        chat_stream_runtime=chat_stream_runtime,
        chat_audio_agent=chat_audio_agent,
        chat_code_agent=chat_code_agent,
    )
    return ctx


def meal_deps(ctx: AppContext) -> MealDeps:
    return MealDeps(settings=ctx.settings, stores=ctx.stores, event_timeline=ctx.event_timeline)


def recommendation_deps(ctx: AppContext) -> RecommendationDeps:
    return RecommendationDeps(stores=ctx.stores, clinical_memory=ctx.clinical_memory)


def workflow_deps(ctx: AppContext) -> WorkflowDeps:
    return WorkflowDeps(
        settings=ctx.settings,
        stores=ctx.stores,
        event_timeline=ctx.event_timeline,
    )


def emotion_deps(ctx: AppContext) -> EmotionDeps:
    return EmotionDeps(
        settings=ctx.settings,
        emotion_agent=ctx.emotion_agent,
        event_timeline=ctx.event_timeline,
    )


def chat_deps(ctx: AppContext, session: dict[str, object]) -> ChatDeps:
    user_id = str(session.get("user_id"))
    session_id = str(session.get("session_id"))
    chat_memory = MemoryManager(
        user_id=user_id,
        session_id=session_id,
        inference_engine=ctx.chat_inference_engine,
    )
    chat_orchestrator = ChatOrchestrator(
        router=ctx.chat_router,
        memory=chat_memory,
    )
    chat_health_tracker = HealthTracker(
        user_id=user_id,
        session_id=session_id,
        inference_engine=ctx.chat_inference_engine,
    )
    return ChatDeps(
        chat_agent=chat_orchestrator,
        audio_agent=ctx.chat_audio_agent,
        emotion_agent=ctx.emotion_agent,
        health_tracker=chat_health_tracker,
        code_agent=ctx.chat_code_agent,
        event_timeline=ctx.event_timeline,
    )


def recommendation_agent_deps(ctx: AppContext) -> RecommendationAgentDeps:
    return RecommendationAgentDeps(
        stores=ctx.stores,
        clinical_memory=ctx.clinical_memory,
        recommendation_agent=ctx.recommendation_agent,
    )


def alert_deps(ctx: AppContext) -> AlertDeps:
    return AlertDeps(
        stores=ctx.stores,
        tool_registry=ctx.tool_registry,
        event_timeline=ctx.event_timeline,
    )


def clinical_card_deps(ctx: AppContext) -> ClinicalCardDeps:
    return ClinicalCardDeps(stores=ctx.stores)
