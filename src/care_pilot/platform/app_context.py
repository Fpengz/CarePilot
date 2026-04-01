"""
Central service registry and runtime context for CarePilot.

This module provides the AppContext container which assembles shared services,
repositories, agents, and platform adapters.
"""

from __future__ import annotations

import logging
import os
from functools import cached_property
from typing import Any, cast

import logfire
from care_pilot.agent.core import AgentRegistry, build_default_agent_registry
from care_pilot.agent.emotion.agent import EmotionAgent
from care_pilot.agent.emotion.schemas import EmotionInferenceResult, EmotionRuntimeHealth
from care_pilot.agent.recommendation.agent import RecommendationAgent
from care_pilot.agent.runtime.chat_runtime import (
    ChatRuntimeConfig,
    ChatStreamRuntime,
    build_chat_inference_engine,
    build_chat_runtime_config,
)
from care_pilot.agent.runtime.inference_engine import InferenceEngine
from care_pilot.config.app import AppSettings as Settings, get_settings
from care_pilot.config.llm import LLMCapability
from care_pilot.features.companion.chat.audio_adapter import AudioAgent
from care_pilot.features.companion.chat.code_adapter import CodeAgent
from care_pilot.features.companion.chat.router import QueryRouter
from care_pilot.features.companion.chat.search_adapter import SearchAgent
from care_pilot.features.companion.core.projectors import CompanionSnapshotProjector
from care_pilot.features.companion.emotion.config import EmotionRuntimeConfig
from care_pilot.features.companion.emotion.ports import EmotionInferencePort
from care_pilot.features.companion.emotion.remote_runtime import RemoteEmotionRuntime
from care_pilot.features.companion.emotion.runtime import InProcessEmotionRuntime
from care_pilot.platform.auth import InMemoryAuthStore, SessionSigner, SQLiteAuthStore
from care_pilot.platform.cache import (
    ClinicalSnapshotMemoryService,
    EventTimelineService,
    InMemoryCacheStore,
    ProfileMemoryService,
    RedisCacheStore,
)
from care_pilot.platform.eventing import EventProjectionRegistry, EventReactionRegistry
from care_pilot.platform.eventing.models import DeliverySemantics, OrderingScope
from care_pilot.platform.eventing.reactions import AgentProposalCacheReaction
from care_pilot.platform.memory import MemoryStore, build_memory_store
from care_pilot.platform.observability.tooling.platform_registry import build_platform_tool_registry
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

logger = logging.getLogger(__name__)

AuthStore = InMemoryAuthStore | SQLiteAuthStore
CacheStore = InMemoryCacheStore | RedisCacheStore
CoordinationStore = InMemoryCoordinationStore | RedisCoordinationStore
HouseholdStore = SQLiteHouseholdStore


class AppContext:
    """
    Service registry and runtime context for CarePilot.

    AppContext acts as a central hub for shared services, repositories,
    and agent runtimes. It handles the lifecycle of heavy components (like
    ML model engines) and provides lazy access to agents through cached
    properties.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        app_store: AppStoreBackend,
        stores: AppStores,
        profile_memory: ProfileMemoryService,
        clinical_memory: ClinicalSnapshotMemoryService,
        event_timeline: EventTimelineService,
        event_reactions: EventReactionRegistry,
        event_projections: EventProjectionRegistry,
        tool_registry: ToolRegistry,
        agent_registry: AgentRegistry,
        auth_store: AuthStore,
        session_signer: SessionSigner,
        memory_store: MemoryStore,
        notification_reads: Any,
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
        self.event_reactions = event_reactions
        self.event_projections = event_projections
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
        transcription_api_key = os.environ.get("TRANSCRIPTION_API_KEY") or os.environ.get(
            "QWEN_API_KEY"
        )
        transcription_base_url = os.environ.get("TRANSCRIPTION_BASE_URL") or os.environ.get(
            "QWEN_BASE_URL"
        )
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


def build_app_context() -> AppContext:
    # This is a bit of a shim to avoid circular imports if any
    from care_pilot.features.reminders.notifications.notification_service import (
        NotificationReadStateStore,
    )
    from care_pilot.platform.persistence.household import SQLiteHouseholdStore

    settings = get_settings()
    app_store = build_app_store(settings)
    stores = build_app_stores(app_store)
    profile_memory = ProfileMemoryService()
    clinical_memory = ClinicalSnapshotMemoryService()
    event_timeline = EventTimelineService(
        repository=app_store,
        persistence_enabled=settings.workers.workflow_trace_persistence_enabled,
    )
    event_reactions = EventReactionRegistry()
    event_projections = EventProjectionRegistry()

    cache_store = _build_cache_store(settings)

    _register_event_handlers(
        event_projections=event_projections,
        event_reactions=event_reactions,
        stores=stores,
        clinical_memory=clinical_memory,
        cache_store=cache_store,
    )

    tool_registry = build_platform_tool_registry(app_store)
    agent_registry = build_default_agent_registry()
    auth_store = _build_auth_store(settings)
    memory_store = build_memory_store(settings)
    session_signer = SessionSigner(settings.auth.session_secret)
    notification_reads = NotificationReadStateStore()
    coordination_store = _build_coordination_store(settings)
    household_store = SQLiteHouseholdStore(settings.storage.api_sqlite_db_path)
    chat_runtime_config = build_chat_runtime_config(settings)

    ctx = AppContext(
        settings=settings,
        app_store=app_store,
        stores=stores,
        profile_memory=profile_memory,
        clinical_memory=clinical_memory,
        event_timeline=event_timeline,
        event_reactions=event_reactions,
        event_projections=event_projections,
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


async def close_app_context(ctx: AppContext) -> None:
    logfire.debug(f"closing app context {id(ctx)}")
    # Use __dict__ to check if cached properties were ever accessed
    # to avoid re-instantiating them during shutdown.

    # Non-lazy components first
    components_to_close = [
        ctx.app_store,
        ctx.auth_store,
        ctx.household_store,
        ctx.cache_store,
        ctx.coordination_store,
    ]

    for component in components_to_close:
        close = getattr(component, "close", None)
        if callable(close):
            import inspect

            if inspect.iscoroutinefunction(close):
                await close()
            else:
                close()

    # Lazy components (cached_properties)
    if "emotion_agent" in ctx.__dict__:
        agent = ctx.emotion_agent
        close_func = getattr(agent._runtime, "close", None)
        if callable(close_func):
            import inspect

            if inspect.iscoroutinefunction(close_func):
                await close_func()
            else:
                close_func()

    if "chat_audio_agent" in ctx.__dict__:
        close_func = getattr(ctx.chat_audio_agent, "close", None)
        if callable(close_func):
            import inspect

            if inspect.iscoroutinefunction(close_func):
                await close_func()
            else:
                close_func()


def _build_auth_store(settings: Settings) -> AuthStore:
    if settings.auth.store_backend == "in_memory":
        return InMemoryAuthStore(settings)
    return SQLiteAuthStore(settings=settings, db_path=settings.auth.sqlite_db_path)


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


def _register_event_handlers(
    event_projections: EventProjectionRegistry,
    event_reactions: EventReactionRegistry,
    stores: AppStores,
    clinical_memory: ClinicalSnapshotMemoryService,
    cache_store: CacheStore,
) -> None:
    """Register all event projections and reactions."""
    health_metrics = ChatHealthMetricsRepository()
    event_projections.register(
        CompanionSnapshotProjector(
            name="companion_snapshot_projector",
            event_types=[
                "meal_analyzed",
                "meal_confirmed",
                "meal_skipped",
                "medication_logged",
                "medication_updated",
                "medication_deleted",
                "adherence_updated",
                "symptom_reported",
                "reminder_triggered",
                "reminder_confirmed",
                "reminder_scheduled",
                "profile_updated",
                "profile_onboarding_step",
                "profile_onboarding_completed",
            ],
            projection_section="patient_case_snapshot",
            projection_version="v1",
            ordering_scope=OrderingScope.PER_PATIENT,
            stores=stores,
            clinical_memory=clinical_memory,
            health_metrics=health_metrics,
        )
    )

    event_reactions.register(
        AgentProposalCacheReaction(
            name="agent_proposal_cache",
            event_types=["agent_action_proposed"],
            delivery_semantics=DeliverySemantics.AT_LEAST_ONCE,
            ordering_scope=OrderingScope.PER_PATIENT,
            cache_store=cache_store,
        )
    )
