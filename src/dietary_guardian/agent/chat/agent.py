"""
Implement the companion chat agent.

This module manages chat sessions, routes user queries, and calls the
SEA-LION-compatible LLM runtime to generate responses.

Example:
    agent = ChatAgent(client, model_id="gpt-4.1-mini", router=router)
    async for chunk in agent.stream_async(message, client, agent.model_id):
        ...
"""

import asyncio
import json
import sqlite3
from typing import AsyncIterator, TYPE_CHECKING

from openai import OpenAI

from dietary_guardian.agent.chat.memory import MemoryManager

if TYPE_CHECKING:
    from dietary_guardian.agent.chat.router import QueryRouter

SYSTEM_PROMPT = (
    "You are SEA-LION, a helpful health assistant specialised in Singapore's food, "
    "medications, and chronic-disease management (diabetes, hypertension, cardiovascular). "
    "Answer concisely and accurately. When relevant, reference Singapore-specific "
    "guidelines or food culture."
)


class ChatAgent:
    """Agent that manages chat history and calls the SEA-LION LLM."""

    def __init__(
        self,
        client: OpenAI,
        model_id: str | None = None,
        router: "QueryRouter | None" = None,
        session_id: str = "default",
    ) -> None:
        self.model_id = model_id or "aisingapore/Gemma-SEA-LION-v4-27B-IT"
        self.client = client
        self.router = router
        self.memory = MemoryManager(
            session_id=session_id,
            client=self.client,
            model_id=self.model_id,
        )

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def build_api_messages(
        self,
        extra_context: str | None = None,
        emotion_context: str | None = None,
    ) -> list[dict]:
        """Build the messages list with a single leading system message.

        All system-level content (prompt + rolling summary + short-term label)
        is merged into one system message so the API never sees two consecutive
        system roles (which the SEA-LION endpoint rejects).
        """
        ctx             = self.memory.build_prompt_context()
        rolling_summary = ctx["rolling_summary"]
        short_term      = ctx["short_term"]

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

        for m in short_term:
            api_messages.append({"role": m["role"], "content": m["content"]})

        # Augment the last user message with retrieval context
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

        print("[ChatAgent] api_messages:\n" + json.dumps(api_messages, indent=2, ensure_ascii=False))
        return api_messages

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    async def route_async(self, user_message: str) -> str | None:
        """Run the synchronous router in a thread pool (non-blocking)."""
        if self.router is None:
            return None
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self.router.route, user_message)
        return result.context

    # ------------------------------------------------------------------
    # Streaming (async — FastAPI / SSE)
    # ------------------------------------------------------------------

    async def stream_async(
        self,
        user_message: str,
        async_client,
        model_id: str | None = None,
        emotion_context: str | None = None,
    ) -> AsyncIterator[str]:
        """Full pipeline: persist → route → build prompt → stream → persist reply.

        Yields SSE-formatted strings:
            data: {"text": "token"}
            data: {"done": true}
            data: {"error": "..."}   (on failure)
        """
        model_id = model_id or self.model_id

        self.memory.add_message("user", user_message)

        # [TRACK] messages are stored for the health dashboard — no LLM needed
        if user_message.upper().startswith("[TRACK]"):
            self.memory.add_message("assistant", "Tracked.")
            yield f"data: {json.dumps({'text': 'Tracked.'})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
            return

        extra_context = await self.route_async(user_message)
        api_messages  = self.build_api_messages(extra_context, emotion_context)

        full_response = ""
        try:
            stream = await async_client.chat.completions.create(
                model=model_id,
                messages=api_messages,
                stream=True,
            )
            async for chunk in stream:
                token = (chunk.choices[0].delta.content or "") if chunk.choices else ""
                if token:
                    full_response += token
                    yield f"data: {json.dumps({'text': token})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

        if full_response:
            self.memory.add_message("assistant", full_response)

        yield f"data: {json.dumps({'done': True})}\n\n"

    # ------------------------------------------------------------------
    # History management
    # ------------------------------------------------------------------

    def clear_history(self) -> None:
        """Delete all messages/summaries for this session from SQLite and memory."""
        db_path    = str(self.memory._db_path)
        session_id = self.memory._session_id
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM chat_summaries WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
        self.memory._messages          = []
        self.memory._rolling_summary   = ""
        self.memory._summarized_up_to  = 0
