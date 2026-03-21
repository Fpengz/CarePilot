"""
Orchestrate chat workflows.

This module coordinates memory, routing, and inference for the companion chat
using a multi-agent LangGraph system.
"""

from __future__ import annotations

import asyncio
import re
import sqlite3
import uuid
from collections.abc import AsyncIterator
from typing import Any, Literal, cast

from fastapi import HTTPException, Request
from langchain_core.messages import HumanMessage

from care_pilot.agent.chat.schemas import (
    ChatStreamEvent,
)
from care_pilot.agent.emotion import (
    EmotionAgentDisabledError,
)
from care_pilot.agent.emotion.schemas import EmotionInferenceResult
from care_pilot.features.companion.chat.meal_intent import (
    classify_meal_log_intent,
    heuristic_meal_log_intent,
    meal_proposal_cache_key,
)
from care_pilot.features.companion.chat.memory import MemoryManager
from care_pilot.features.companion.chat.memory_store import (
    build_memory_context as build_memory_snippet_context,
)
from care_pilot.features.companion.chat.memory_store import (
    fetch_memory_snippets,
    record_chat_turn,
)
from care_pilot.features.companion.chat.router import QueryRouter
from care_pilot.features.companion.chat.workflows.companion_graph import (
    CompanionState,
    build_companion_graph,
)

# Important: These must be imported from features core, not apps/api
from care_pilot.features.companion.core.companion_core_service import CompanionStateInputs
from care_pilot.features.companion.core.domain import PatientCaseSnapshot
from care_pilot.features.companion.core.snapshot import build_case_snapshot
from care_pilot.features.meals.domain.normalization import log_meal_from_text
from care_pilot.platform.observability import get_logger
from care_pilot.platform.persistence import AppStores

logger = get_logger(__name__)

_MEAL_PREFIX_RE = re.compile(r"^(?:log\s+meal|meal)\s*:\s*(.+)$", re.IGNORECASE)


class ChatOrchestrator:
    """Manages the multi-agent chat pipeline via LangGraph."""

    def __init__(
        self,
        *,
        router: QueryRouter | None,
        memory: MemoryManager,
    ) -> None:
        self.router = router
        self.memory = memory
        self._graph = build_companion_graph().compile()

    async def run_multi_agent_workflow(
        self, user_message: str, snapshot: PatientCaseSnapshot
    ) -> dict[str, Any]:
        """Run the Supervisor-led LangGraph workflow."""
        initial_state: CompanionState = {
            "snapshot": snapshot,
            "messages": [HumanMessage(content=user_message)],
            "next_agent": None,
            "last_agent_response": None,
            "errors": [],
            "session_id": self.memory._session_id or "default_session",
        }

        result = await self._graph.ainvoke(initial_state)
        return result

    async def stream_events(
        self,
        *,
        user_message: str,
        request: Request,
        session: dict[str, object],
        ctx: Any,  # AppContext (duck typed to avoid cycle)
        inputs: CompanionStateInputs,
    ) -> AsyncIterator[ChatStreamEvent]:
        """
        Stream multi-agent events from the LangGraph.
        """
        user_id = str(session.get("user_id", ""))
        session_id = str(session.get("session_id", ""))

        # 1. Build Blackboard (Snapshot)
        snapshot = build_case_snapshot(
            user_profile=inputs.user_profile,
            health_profile=inputs.health_profile,
            meals=inputs.meals,
            reminders=inputs.reminders,
            adherence_events=inputs.adherence_events,
            symptoms=inputs.symptoms,
            biomarker_readings=inputs.biomarker_readings,
            blood_pressure_readings=inputs.blood_pressure_readings,
            clinical_snapshot=inputs.clinical_snapshot,
        )

        # 2. Emotion Logic
        if ctx.emotion_agent.inference_enabled:
            try:
                loop = asyncio.get_running_loop()
                inference = await loop.run_in_executor(
                    None,
                    lambda: ctx.emotion_agent.infer_text(text=user_message),
                )
                yield ChatStreamEvent(
                    event="emotion",
                    data={
                        "emotion": inference.final_emotion,
                        "score": inference.confidence,
                        "product_state": inference.product_state,
                    },
                )
            except EmotionAgentDisabledError:
                pass
            except Exception as exc:  # noqa: BLE001
                self._log_suppressed_emotion_failure(request=request, phase="emotion", exc=exc)

        # 3. Memory & Supplemental context
        memory_context = None
        if ctx.memory_store.enabled:
            snippets = await fetch_memory_snippets(
                memory_store=ctx.memory_store,
                user_id=user_id,
                query=user_message,
                limit=ctx.settings.memory.top_k,
            )
            if snippets:
                memory_context = build_memory_snippet_context(snippets)

        if memory_context:
            user_message_with_memory = f"{user_message}\n\n{memory_context}"
        else:
            user_message_with_memory = user_message

        # 4. Meal Intent (Ported from legacy orchestrator)
        meal_text = self._parse_meal_command(user_message)
        response_prefix = None
        if not meal_text:
            intent_result, needs_llm = heuristic_meal_log_intent(user_message)
            if needs_llm:
                from apps.api.carepilot_api.services.companion_orchestration import (
                    load_companion_inputs,
                )
                inputs_for_intent = load_companion_inputs(context=ctx, session=session) # Re-load for intent if needed
                del inputs_for_intent # Not used directly but showing intent pattern
                intent_result = await classify_meal_log_intent(
                    user_message, engine=ctx.chat_inference_engine
                )
            if intent_result.intent and intent_result.meal_text:
                proposal_id = str(uuid.uuid4())
                cache_key = meal_proposal_cache_key(
                    user_id=user_id,
                    session_id=session_id,
                    proposal_id=proposal_id,
                )
                ctx.cache_store.set_json(
                    cache_key,
                    {
                        "proposal_id": proposal_id,
                        "user_id": user_id,
                        "session_id": session_id,
                        "meal_text": intent_result.meal_text,
                        "reason": intent_result.reason,
                    },
                    ttl_seconds=600,
                )
                prompt = self._meal_proposal_prompt(intent_result.meal_text)
                response_prefix = f"{prompt}\n\n"
                yield ChatStreamEvent(
                    event="meal_proposed",
                    data={
                        "proposal_id": proposal_id,
                        "meal_text": intent_result.meal_text,
                        "prompt": prompt,
                        "reason": intent_result.reason,
                    },
                )

        if meal_text:
            meal_result = self._log_meal_command(
                user_id=user_id,
                meal_text=meal_text,
                stores=ctx.stores,
            )
            response_prefix = f"{meal_result['message']}\n\n"
            yield ChatStreamEvent(
                event="meal_logged",
                data=cast(dict[str, object], meal_result)
            )

        # 5. Run Graph
        try:
            # We use the version with memory context for the agent reasoning
            result = await self.run_multi_agent_workflow(user_message_with_memory, snapshot)
            final_response = ""

            last_resp = result.get("last_agent_response")
            if last_resp:
                final_response = last_resp.summary
                if response_prefix:
                    final_response = f"{response_prefix}{final_response}"
                yield ChatStreamEvent(event="token", data={"text": final_response})
            else:
                final_response = "I've updated your care context based on our conversation."
                if response_prefix:
                    final_response = f"{response_prefix}{final_response}"
                yield ChatStreamEvent(event="token", data={"text": final_response})

            # 6. Persistence
            if final_response:
                self.memory.add_message("user", user_message)
                self.memory.add_message("assistant", final_response)
                await record_chat_turn(
                    memory_store=ctx.memory_store,
                    user_id=user_id,
                    session_id=session_id,
                    user_message=user_message,
                    assistant_message=final_response,
                    metadata={"source": "chat_multi_agent"},
                )

        except Exception as exc:  # noqa: BLE001
            logger.error("multi_agent_workflow_failed error=%s", exc)
            yield ChatStreamEvent(
                event="error",
                data={"message": str(exc), "phase": "orchestration", "retryable": False},
            )

        yield ChatStreamEvent(event="done", data={"status": "complete"})

    async def stream_audio_events(
        self,
        *,
        audio_bytes: bytes,
        filename: str,
        content_type: str | None,
        request: Request,
        session: dict[str, object],
        ctx: Any,  # AppContext
        inputs: CompanionStateInputs,
    ) -> AsyncIterator[ChatStreamEvent]:
        # 1. Transcription
        try:
            # Transcribe audio using the directly available audio agent
            user_message = await ctx.chat_audio_agent.transcribe_bytes(audio_bytes, filename)
        except Exception as exc:

            yield ChatStreamEvent(
                event="error",
                data={"message": f"Transcription failed: {exc}", "phase": "audio"}
            )
            return

        if not user_message:
            yield ChatStreamEvent(
                event="error",
                data={"message": "Transcription returned empty text", "phase": "audio"}
            )
            return

        yield ChatStreamEvent(event="transcribed", data={"text": user_message})

        # 2. Speech Emotion
        if ctx.emotion_agent.inference_enabled and ctx.emotion_agent.speech_enabled:
            try:
                loop = asyncio.get_running_loop()
                inference = await loop.run_in_executor(
                    None,
                    lambda: ctx.emotion_agent.infer_speech(
                        audio_bytes=audio_bytes,
                        filename=filename,
                        content_type=content_type,
                        transcription=user_message,
                    ),
                )
                yield ChatStreamEvent(
                    event="emotion",
                    data={
                        "emotion": inference.final_emotion,
                        "score": inference.confidence,
                        "product_state": inference.product_state,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                self._log_suppressed_emotion_failure(
                    request=request, phase="speech_emotion", exc=exc
                )

        # 3. Follow with normal stream
        async for event in self.stream_events(
            user_message=user_message,
            request=request,
            session=session,
            ctx=ctx,
            inputs=inputs,
        ):
            yield event

    async def confirm_meal_log(
        self,
        *,
        proposal_id: str,
        action: Literal["confirm", "skip"],
        request: Request,  # noqa: ARG002
        session: dict[str, object],
        ctx: Any,  # AppContext
        inputs: CompanionStateInputs,  # noqa: ARG002
    ) -> dict[str, object]:
        user_id = str(session.get("user_id", ""))
        session_id = str(session.get("session_id", ""))
        cache_key = meal_proposal_cache_key(
            user_id=user_id,
            session_id=session_id,
            proposal_id=proposal_id,
        )
        proposal = ctx.cache_store.get_json(cache_key)
        if proposal is None:
            raise HTTPException(status_code=404, detail="meal proposal not found")

        meal_text = str(proposal.get("meal_text", "")).strip()

        if action == "skip":
            ctx.cache_store.delete(cache_key)
            return {"status": "skipped", "assistant_followup": "Skipped logging this meal."}

        # Log it
        meal_result = self._log_meal_command(user_id=user_id, meal_text=meal_text, stores=ctx.stores)
        ctx.cache_store.delete(cache_key)

        return {
            "status": "logged",
            "meal_name": meal_result["meal_name"],
            "message": meal_result["message"],
            "event_id": meal_result["event_id"],
            "assistant_followup": f"Confirmed. {meal_result['message']}",
        }

    # Internal helpers

    def _parse_meal_command(self, message: str) -> str | None:
        cleaned = message.strip()
        if not cleaned:
            return None
        if cleaned.lower().startswith("[meal]"):
            return cleaned[6:].strip() or None
        match = _MEAL_PREFIX_RE.match(cleaned)
        return match.group(1).strip() if match else None

    def _format_emotion_context(self, inference: EmotionInferenceResult) -> str:
        pct = int(inference.confidence * 100)
        return (
            f"[Emotional context] The user appears to be feeling **{inference.final_emotion}** "
            f"(confidence {pct} %). Please respond with appropriate empathy and tailor "
            f"your advice to their current emotional state."
        )

    def _meal_proposal_prompt(self, meal_text: str) -> str:
        return f"I can log **{meal_text}** as a meal. Would you like me to save it?"

    def _log_meal_command(
        self,
        *,
        user_id: str,
        meal_text: str,
        stores: AppStores,
        locale: str = "en-SG",
    ) -> dict[str, Any]:
        result = log_meal_from_text(
            user_id=user_id,
            meal_text=meal_text,
            food_store=stores.foods,
            meals_store=stores.meals,
            locale=locale,
        )
        return {
            "event_id": result.validated_event.event_id,
            "meal_name": result.validated_event.meal_name,
            "message": f"Logged meal: {meal_text.strip()}.",
        }

    def _log_suppressed_emotion_failure(self, request: Request, phase: str, exc: Exception) -> None:
        logger.warning(
            "chat_emotion_inference_suppressed phase=%s request_id=%s error=%s",
            phase,
            getattr(request.state, "request_id", None),
            exc,
        )

    def clear_history(self) -> None:
        """Delete all messages/summaries for this user."""
        db_path = str(self.memory._db_path)
        user_id = self.memory._user_id
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM chat_summaries WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        self.memory._messages = []
        self.memory._rolling_summary = ""
        self.memory._summarized_up_to = 0
