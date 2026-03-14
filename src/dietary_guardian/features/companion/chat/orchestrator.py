"""
Orchestrate chat workflows.

This module coordinates memory, routing, and inference for the companion chat.
"""

from __future__ import annotations

import asyncio
import sqlite3
from typing import AsyncIterator

from dietary_guardian.agent.chat.agent import run_chat
from dietary_guardian.features.companion.chat.memory import MemoryManager
from dietary_guardian.features.companion.chat.router import QueryRouter
from dietary_guardian.features.companion.chat.routes.base import RouteResult
from dietary_guardian.agent.chat.schemas import (
    ChatInput,
    ChatOutput,
    ChatRouteLabel,
    ChatStreamEvent,
)
from dietary_guardian.platform.observability import get_logger

logger = get_logger(__name__)


class ChatOrchestrator:
    """Manages the full chat pipeline: persist → route → infer → persist."""

    def __init__(
        self,
        *,
        router: QueryRouter | None,
        memory: MemoryManager,
    ) -> None:
        self.router = router
        self.memory = memory

    async def route_async(self, user_message: str) -> RouteResult:
        """Run the synchronous router in a thread pool (non-blocking)."""
        if self.router is None:
            return RouteResult(route_name=ChatRouteLabel.GENERAL, context=None)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.router.route, user_message)

    async def stream_events(
        self,
        *,
        user_message: str,
        emotion_context: str | None = None,
        extra_context: str | None = None,
        response_prefix: str | None = None,
    ) -> AsyncIterator[ChatStreamEvent]:
        """Full pipeline: persist → route → build prompt → run_chat → persist reply."""
        self.memory.add_message("user", user_message)

        if user_message.upper().startswith("[TRACK]"):
            self.memory.add_message("assistant", "Tracked.")
            yield ChatStreamEvent(event="token", data={"text": "Tracked."})
            yield ChatStreamEvent(event="done", data={"status": "tracked"})
            return

        del extra_context
        
        # Build prompt context from memory
        ctx = self.memory.build_prompt_context()
        history = ctx["short_term"]
        
        full_response = ""
        if response_prefix:
            full_response = response_prefix
            yield ChatStreamEvent(event="token", data={"text": response_prefix})

        try:
            # For now, we call the agent non-streaming
            # In a full pydantic_ai refactor, we'd use agent.run_stream()
            response = await run_chat(
                message=user_message,
                history=history,
                system_prompt_override=emotion_context,
            )
            # Simulate streaming for now if needed, or just yield the whole response
            yield ChatStreamEvent(event="token", data={"text": response})
            full_response += response
        except Exception as exc:  # noqa: BLE001
            logger.warning("chat_orchestrator_failed error=%s", exc)
            yield ChatStreamEvent(
                event="error",
                data={"message": str(exc), "phase": "stream", "retryable": False},
            )
        else:
            if full_response:
                self.memory.add_message("assistant", full_response)
        finally:
            yield ChatStreamEvent(event="done", data={"status": "complete"})

    async def run_chat_workflow(self, input_data: ChatInput) -> ChatOutput:
        """Execute a non-streaming chat request for internal workflows."""
        self.memory.add_message("user", input_data.message)
        route_result = await self.route_async(input_data.message)
        ctx = self.memory.build_prompt_context()
        history = ctx["short_term"]
        
        response = await run_chat(
            message=input_data.message,
            history=history,
            system_prompt_override=input_data.emotion_context,
        )
        if response:
            self.memory.add_message("assistant", response)
            
        return ChatOutput(
            response=response,
            route=route_result.route_name,
            context_used=bool(route_result.context),
        )

    def clear_history(self) -> None:
        """Delete all messages/summaries for this session."""
        db_path = str(self.memory._db_path)
        session_id = self.memory._session_id
        user_id = self.memory._user_id
        conn = sqlite3.connect(db_path)
        conn.execute(
            "DELETE FROM chat_messages WHERE user_id = ? AND session_id = ?",
            (user_id, session_id),
        )
        conn.execute(
            "DELETE FROM chat_summaries WHERE user_id = ? AND session_id = ?",
            (user_id, session_id),
        )
        conn.commit()
        conn.close()
        self.memory._messages = []
        self.memory._rolling_summary = ""
        self.memory._summarized_up_to = 0
