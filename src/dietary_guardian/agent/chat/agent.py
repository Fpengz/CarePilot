"""
Implement the companion chat agent.

This module manages chat sessions, routes user queries, and executes
SEA-LION-compatible chat completions with streaming SSE events.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from typing import AsyncIterator, Literal

from dietary_guardian.agent.chat.memory import MemoryManager
from dietary_guardian.agent.chat.routes.base import RouteResult
from dietary_guardian.agent.chat.schemas import ChatInput, ChatOutput, ChatRouteLabel
from dietary_guardian.agent.chat.router import QueryRouter
from dietary_guardian.agent.core.base import AgentContext, AgentResult, BaseAgent
from dietary_guardian.agent.runtime.chat_runtime import ChatStreamRuntime
from dietary_guardian.platform.observability import get_logger

SYSTEM_PROMPT = (
    "You are SEA-LION, a helpful health assistant specialised in Singapore's food, "
    "medications, and chronic-disease management (diabetes, hypertension, cardiovascular). "
    "Answer concisely and accurately. When relevant, reference Singapore-specific "
    "guidelines or food culture."
)

ChatEvent = Literal["token", "emotion", "transcribed", "error", "done"]


class ChatAgent(BaseAgent[ChatInput, ChatOutput]):
    """Agent that manages chat history and calls the SEA-LION LLM."""

    name = "chat_agent"
    input_schema = ChatInput
    output_schema = ChatOutput

    def __init__(
        self,
        *,
        stream_runtime: ChatStreamRuntime,
        router: QueryRouter | None,
        memory: MemoryManager,
        model_id: str | None = None,
    ) -> None:
        self.model_id = model_id or "aisingapore/Gemma-SEA-LION-v4-27B-IT"
        self._stream_runtime = stream_runtime
        self.router = router
        self.memory = memory
        self._logger = get_logger(__name__)

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def build_api_messages(
        self,
        extra_context: str | None = None,
        emotion_context: str | None = None,
    ) -> list[dict]:
        """Build the messages list with a single leading system message."""
        ctx = self.memory.build_prompt_context()
        rolling_summary = ctx["rolling_summary"]
        short_term = ctx["short_term"]

        system_parts = [SYSTEM_PROMPT]
        if emotion_context:
            system_parts.append(emotion_context)
        if rolling_summary:
            system_parts.append(f"Previous conversation summary:\n{rolling_summary}")
        if short_term:
            system_parts.append(
                f"Latest {len(short_term)} conversation message(s) after summary:"
            )

        api_messages: list[dict] = [
            {"role": "system", "content": "\n\n".join(system_parts)}
        ]

        normalized = self._normalize_messages(short_term)
        for message in normalized:
            api_messages.append({"role": message["role"], "content": message["content"]})

        if extra_context and api_messages and api_messages[-1]["role"] == "user":
            api_messages[-1] = {
                "role": "user",
                "content": (
                    extra_context
                    + "\n\n---\n"
                    + api_messages[-1]["content"]
                    + "\n\nPlease answer my question above using the extra context provided."
                ),
            }

        return api_messages

    @staticmethod
    def _normalize_messages(messages: list[dict]) -> list[dict]:
        """Ensure messages alternate user/assistant and start with user."""
        filtered = [m for m in messages if m.get("role") in {"user", "assistant"}]
        # Drop leading assistant messages so we start with a user.
        while filtered and filtered[0]["role"] != "user":
            filtered.pop(0)
        if not filtered:
            return []
        merged: list[dict] = []
        for msg in filtered:
            role = msg["role"]
            content = msg["content"]
            if merged and merged[-1]["role"] == role:
                merged[-1]["content"] += "\n\n" + content
            else:
                merged.append({"role": role, "content": content})
        return merged

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    async def route_async(self, user_message: str) -> RouteResult:
        """Run the synchronous router in a thread pool (non-blocking)."""
        if self.router is None:
            return RouteResult(route_name=ChatRouteLabel.GENERAL, context=None)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.router.route, user_message)

    # ------------------------------------------------------------------
    # Streaming (async — FastAPI / SSE)
    # ------------------------------------------------------------------

    async def stream(
        self,
        *,
        user_message: str,
        emotion_context: str | None = None,
        model_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Full pipeline: persist → route → build prompt → stream → persist reply."""
        model_id = model_id or self.model_id
        self.memory.add_message("user", user_message)

        if user_message.upper().startswith("[TRACK]"):
            self.memory.add_message("assistant", "Tracked.")
            yield self._format_event("token", {"text": "Tracked."})
            yield self._format_event("done", {"status": "tracked"})
            return

        route_result = await self.route_async(user_message)
        api_messages = self.build_api_messages(route_result.context, emotion_context)

        full_response = ""
        try:
            async for token in self._stream_runtime.stream(messages=api_messages, model_id=model_id):
                full_response += token
                yield self._format_event("token", {"text": token})
        except Exception as exc:  # noqa: BLE001
            self._logger.warning("chat_stream_failed error=%s", exc)
            yield self._format_event(
                "error",
                {"message": str(exc), "phase": "stream", "retryable": False},
            )
        else:
            if full_response:
                self.memory.add_message("assistant", full_response)
        finally:
            yield self._format_event("done", {"status": "complete"})

    # ------------------------------------------------------------------
    # BaseAgent contract
    # ------------------------------------------------------------------

    async def run(self, input_data: ChatInput, context: AgentContext) -> AgentResult[ChatOutput]:
        """Execute a non-streaming chat request for internal workflows."""
        self.memory.add_message("user", input_data.message)
        route_result = await self.route_async(input_data.message)
        api_messages = self.build_api_messages(route_result.context, input_data.emotion_context)
        response = await self._stream_runtime.complete(messages=api_messages, model_id=self.model_id)
        if response:
            self.memory.add_message("assistant", response)
        output = ChatOutput(
            response=response,
            route=route_result.route_name,
            context_used=bool(route_result.context),
        )
        return AgentResult(
            success=True,
            agent_name=self.name,
            output=output,
        )

    # ------------------------------------------------------------------
    # History management
    # ------------------------------------------------------------------

    def clear_history(self) -> None:
        """Delete all messages/summaries for this session from SQLite and memory."""
        db_path = str(self.memory._db_path)
        session_id = self.memory._session_id
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM chat_summaries WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
        self.memory._messages = []
        self.memory._rolling_summary = ""
        self.memory._summarized_up_to = 0

    @staticmethod
    def _format_event(event: ChatEvent, data: dict) -> str:
        payload = {"event": event, "data": data}
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
