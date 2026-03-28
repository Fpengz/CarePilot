"""
Wire API dependencies for runtime stores, agents, and orchestration.

This module provides FastAPI-specific dependency helpers and re-exports
the core AppContext from the platform layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from fastapi import Request

from care_pilot.config.app import AppSettings as Settings
from care_pilot.features.meals.deps import MealDeps
from care_pilot.platform.app_context import AppContext, AuthStore
from care_pilot.platform.auth import SessionSigner
from care_pilot.platform.persistence.health_metrics import ChatHealthMetricsRepository


def get_context(request: Request) -> AppContext:
    """Return the application context from the request state."""
    return cast(AppContext, request.app.state.ctx)


if TYPE_CHECKING:
    from care_pilot.agent.emotion.agent import EmotionAgent
    from care_pilot.agent.recommendation.agent import RecommendationAgent
    from care_pilot.config.app import AppSettings as Settings
    from care_pilot.features.companion.chat.audio_adapter import AudioAgent
    from care_pilot.features.companion.chat.code_adapter import CodeAgent
    from care_pilot.features.companion.chat.health_tracker import HealthTracker
    from care_pilot.features.companion.chat.orchestrator import ChatOrchestrator
    from care_pilot.platform.cache import ClinicalSnapshotMemoryService, EventTimelineService
    from care_pilot.platform.observability.tooling.registry import ToolRegistry
    from care_pilot.platform.persistence import AppStores




@dataclass(frozen=True)
class RecommendationDeps:
    stores: AppStores
    clinical_memory: ClinicalSnapshotMemoryService
    event_timeline: EventTimelineService


@dataclass(frozen=True)
class RecommendationAgentDeps:
    stores: AppStores
    clinical_memory: ClinicalSnapshotMemoryService
    recommendation_agent: RecommendationAgent
    event_timeline: EventTimelineService


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


def meal_deps(ctx: AppContext) -> MealDeps:
    return MealDeps(
        settings=ctx.settings,
        stores=ctx.stores,
        event_timeline=ctx.event_timeline,
        memory_store=ctx.memory_store,
    )


def recommendation_deps(ctx: AppContext) -> RecommendationDeps:
    return RecommendationDeps(
        stores=ctx.stores,
        clinical_memory=ctx.clinical_memory,
        event_timeline=ctx.event_timeline,
    )


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
    from care_pilot.features.companion.chat.health_tracker import HealthTracker
    from care_pilot.features.companion.chat.memory import MemoryManager
    from care_pilot.features.companion.chat.orchestrator import ChatOrchestrator

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
        event_timeline=ctx.event_timeline,
    )


def alert_deps(ctx: AppContext) -> AlertDeps:
    return AlertDeps(
        stores=ctx.stores,
        tool_registry=ctx.tool_registry,
        event_timeline=ctx.event_timeline,
    )


def clinical_card_deps(ctx: AppContext) -> ClinicalCardDeps:
    return ClinicalCardDeps(stores=ctx.stores, health_metrics=ChatHealthMetricsRepository())
