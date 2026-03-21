"""
Wire API dependencies for runtime stores, agents, and orchestration.

This module assembles shared runtime services used by API route handlers,
including agent registry, persistence, and platform adapters.
"""

import os
from dataclasses import dataclass
from functools import cached_property
from typing import cast

from care_pilot.agent.core import AgentRegistry, build_default_agent_registry
from care_pilot.agent.emotion.agent import EmotionAgent
from care_pilot.agent.emotion.schemas import (
    EmotionInferenceResult,
    EmotionRuntimeHealth,
)
from care_pilot.agent.recommendation.agent import RecommendationAgent
from care_pilot.agent.runtime.chat_runtime import (
    ChatRuntimeConfig,
    ChatStreamRuntime,
    build_chat_inference_engine,
    build_chat_runtime_config,
)
from care_pilot.agent.runtime.inference_engine import InferenceEngine
from care_pilot.config.app import AppSettings as Settings
from care_pilot.config.app import get_settings
from care_pilot.config.llm import LLMCapability
from care_pilot.features.companion.chat.audio_adapter import AudioAgent
from care_pilot.features.companion.chat.code_adapter import CodeAgent
from care_pilot.features.companion.chat.health_tracker import HealthTracker
from care_pilot.features.companion.chat.memory import MemoryManager
from care_pilot.features.companion.chat.orchestrator import ChatOrchestrator
from care_pilot.features.companion.chat.router import QueryRouter
from care_pilot.features.companion.chat.search_adapter import SearchAgent
from care_pilot.features.companion.emotion.config import EmotionRuntimeConfig
from care_pilot.features.companion.emotion.ports import EmotionInferencePort
from care_pilot.features.companion.emotion.remote_runtime import (
    RemoteEmotionRuntime,
)
from care_pilot.features.companion.emotion.runtime import (
    InProcessEmotionRuntime,
)
from care_pilot.features.meals.deps import MealDeps  # noqa: F401
from care_pilot.platform.auth import (
    InMemoryAuthStore,
    SessionSigner,
    SQLiteAuthStore,
)
from care_pilot.platform.cache import (
    ClinicalSnapshotMemoryService,
    EventTimelineService,
    InMemoryCacheStore,
    ProfileMemoryService,
    RedisCacheStore,
)
from care_pilot.platform.memory import MemoryStore, build_memory_store
from care_pilot.platform.observability.tooling.platform_registry import (
    build_platform_tool_registry,
)
from care_pilot.platform.observability.tooling.registry import ToolRegistry
from care_pilot.platform.persistence import (
    AppStoreBackend,
    AppStores,
    build_app_store,
    build_app_stores,
)
from care_pilot.platform.persistence.health_metrics import ChatHealthMetricsRepository
from care_pilot.platform.persistence.household import SQLiteHouseholdStore
from care_pilot.platform.scheduling.coordination import (
    InMemoryCoordinationStore,
    RedisCoordinationStore,
)

from .services.notifications import NotificationReadStateStore

AuthStore = InMemoryAuthStore | SQLiteAuthStore
CacheStore = InMemoryCacheStore | RedisCacheStore
CoordinationStore = InMemoryCoordinationStore | RedisCoordinationStore
HouseholdStore = SQLiteHouseholdStore


class AppContext:
    def __init__(
        self,
        *,
        settings: Settings,
        app_store: AppStoreBackend,
        stores: AppStores,
        profile_memory: ProfileMemoryService,
        clinical_memory: ClinicalSnapshotMemoryService,
        event_timeline: EventTimelineService,
        tool_registry: ToolRegistry,
        agent_registry: AgentRegistry,
        auth_store: AuthStore,
        session_signer: SessionSigner,
        memory_store: MemoryStore,
        notification_reads: NotificationReadStateStore,
        cache_store: CacheStore,
        coordination_store: CoordinationStore,
        household_store: HouseholdStore,
        chat_runtime_config: ChatRuntimeConfig,
    ) -> None:
        self.settings = settings
        self.app_store = app_store
        self.stores = stores
        self.profile_memory = profile_memory
        self.clinical_memory = clinical_memory
        self.event_timeline = event_timeline
        self.tool_registry = tool_registry
        self.agent_registry = agent_registry
        self.auth_store = auth_store
        self.session_signer = session_signer
        self.memory_store = memory_store
        self.notification_reads = notification_reads
        self.cache_store = cache_store
        self.coordination_store = coordination_store
        self.household_store = household_store
        self.chat_runtime_config = chat_runtime_config

    @cached_property
    def emotion_agent(self) -> EmotionAgent:
        settings = self.settings
        if settings.emotion.inference_enabled or settings.emotion.speech_enabled:
            config = EmotionRuntimeConfig.from_settings(settings)
            if settings.emotion.runtime_mode == "remote":
                emotion_runtime = RemoteEmotionRuntime(config, event_timeline=self.event_timeline)
            else:
                emotion_runtime = InProcessEmotionRuntime(
                    config,
                    event_timeline=self.event_timeline,
                )
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
            emotion_runtime = cast(EmotionInferencePort, _DisabledEmotionRuntime())
        return EmotionAgent(
            runtime=emotion_runtime,
            inference_enabled=settings.emotion.inference_enabled,
            speech_enabled=settings.emotion.speech_enabled,
            request_timeout_seconds=settings.emotion.request_timeout_seconds,
        )

    @cached_property
    def recommendation_agent(self) -> RecommendationAgent:
        return RecommendationAgent()

    @cached_property
    def chat_inference_engine(self) -> InferenceEngine:
        return build_chat_inference_engine(
            self.settings, model_id=self.chat_runtime_config.model_id
        )

    @cached_property
    def medication_inference_engine(self) -> InferenceEngine:
        return InferenceEngine(
            settings=self.settings,
            provider=self.settings.llm.provider,
            capability=LLMCapability.MEDICATION_PARSE,
        )

    @cached_property
    def chat_router(self) -> QueryRouter:
        chat_search_agent = SearchAgent(max_results=3)
        chat_reasoning_engine = build_chat_inference_engine(
            self.settings, model_id=self.chat_runtime_config.reasoning_model_id
        )
        return QueryRouter(
            search_agent=chat_search_agent,
            inference_engine=self.chat_inference_engine,
            code_agent=self.chat_code_agent,
            reasoning_engine=chat_reasoning_engine,
        )

    @cached_property
    def chat_stream_runtime(self) -> ChatStreamRuntime:
        return ChatStreamRuntime(self.settings)

    @cached_property
    def chat_audio_agent(self) -> AudioAgent:
        transcription_provider = os.environ.get("TRANSCRIPTION_PROVIDER")
        transcription_api_key = os.environ.get("TRANSCRIPTION_API_KEY") or os.environ.get("QWEN_API_KEY")
        transcription_base_url = os.environ.get("TRANSCRIPTION_BASE_URL") or os.environ.get("QWEN_BASE_URL")
        transcription_model_id = os.environ.get("TRANSCRIPTION_MODEL_ID")
        return AudioAgent(
            repo_id=os.environ.get("TRANSCRIPTION_MODEL_ID"),
            groq_api_key=os.environ.get("GROQ_API_KEY"),
            provider=transcription_provider,
            api_key=transcription_api_key,
            base_url=transcription_base_url,
            model_id=transcription_model_id,
            model_cache_dir=self.settings.chat.model_cache_dir,
            remote_inference_url=self.settings.emotion.remote_base_url,
        )

    @cached_property
    def chat_code_agent(self) -> CodeAgent:
        return CodeAgent(api_key=os.environ.get("E2B_API_KEY"))


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
    health_metrics: ChatHealthMetricsRepository


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

    # Close async clients if they were instantiated
    if "emotion_agent" in ctx.__dict__:
        agent = ctx.emotion_agent
        close_func = getattr(agent._runtime, "close", None)
        if callable(close_func):
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(close_func())
            except RuntimeError:
                pass

    if "chat_audio_agent" in ctx.__dict__:
        import asyncio
        close_func = getattr(ctx.chat_audio_agent, "close", None)
        if callable(close_func):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(close_func())
            except RuntimeError:
                pass


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
    chat_runtime_config = build_chat_runtime_config(settings)

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
        chat_runtime_config=chat_runtime_config,
    )
    return ctx


def meal_deps(ctx: AppContext) -> MealDeps:
    return MealDeps(
        settings=ctx.settings,
        stores=ctx.stores,
        event_timeline=ctx.event_timeline,
        memory_store=ctx.memory_store,
    )


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
    return ClinicalCardDeps(stores=ctx.stores, health_metrics=ChatHealthMetricsRepository())
