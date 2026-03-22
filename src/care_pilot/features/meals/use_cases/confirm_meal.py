"""Confirm or skip a meal candidate."""

from __future__ import annotations

import asyncio
from contextvars import ContextVar
from datetime import UTC, datetime

from care_pilot.agent.adapters.domain_agents import DietaryAgentAdapter
from care_pilot.agent.core.base import AgentContext
from care_pilot.agent.dietary import DietaryAgentInput
from care_pilot.agent.dietary.schemas import DietaryAgentOutput
from care_pilot.features.meals.deps import MealDeps
from care_pilot.features.meals.domain.models import MealCandidateRecord
from care_pilot.platform.observability import get_logger


class MealCandidateNotFoundError(ValueError):
    pass


class MealCandidateInvalidStateError(ValueError):
    pass


logger = get_logger(__name__)
_DIETARY_AGENT_CONTEXT: ContextVar[AgentContext | None] = ContextVar(
    "dietary_agent_context", default=None
)


async def analyze_dietary_request(input_data: DietaryAgentInput) -> DietaryAgentOutput:
    """Run dietary reasoning with adapter context (for test monkeypatching)."""
    context = _DIETARY_AGENT_CONTEXT.get()
    if context is None:
        context = AgentContext(
            user_id="unknown",
            session_id=None,
            request_id=None,
            correlation_id=None,
        )
    adapter = DietaryAgentAdapter()
    result = await adapter.run(input_data, context)
    output = result.output
    if output is None:
        raise ValueError("dietary agent returned no output")
    return output


async def confirm_meal_candidate(
    *,
    deps: MealDeps,
    user_id: str,
    candidate_id: str,
    action: str,
    session_id: str | None,
    user_name: str | None,
) -> MealCandidateRecord:
    record = deps.stores.meals.get_meal_candidate(user_id, candidate_id)
    if record is None:
        raise MealCandidateNotFoundError("meal candidate not found")
    if record.confirmation_status != "pending":
        raise MealCandidateInvalidStateError("meal candidate already resolved")

    now = datetime.now(UTC)
    if action == "skip":
        updated = record.model_copy(update={"confirmation_status": "skipped", "skipped_at": now})
        deps.stores.meals.save_meal_candidate(updated)
        deps.event_timeline.append(
            event_type="meal_skipped",
            workflow_name="meal_analysis",
            correlation_id=updated.correlation_id or updated.candidate_id,
            request_id=updated.request_id,
            user_id=updated.user_id,
            payload={
                "candidate_id": updated.candidate_id,
                "meal_name": updated.candidate_event.meal_name,
            },
        )
        return updated

    if action != "confirm":
        raise MealCandidateInvalidStateError("invalid confirmation action")

    if record.validated_event is None or record.nutrition_profile is None:
        raise MealCandidateInvalidStateError(
            "candidate missing validated event or nutrition profile"
        )

    deps.stores.meals.save_validated_meal_event(record.validated_event)
    deps.stores.meals.save_nutrition_risk_profile(record.nutrition_profile)
    updated = record.model_copy(update={"confirmation_status": "confirmed", "confirmed_at": now})
    deps.stores.meals.save_meal_candidate(updated)
    deps.event_timeline.append(
        event_type="meal_confirmed",
        workflow_name="meal_analysis",
        correlation_id=updated.correlation_id or updated.candidate_id,
        request_id=updated.request_id,
        user_id=updated.user_id,
        payload={
            "candidate_id": updated.candidate_id,
            "meal_name": updated.candidate_event.meal_name,
            "risk_tags": list(updated.candidate_event.risk_tags),
        },
    )

    try:
        dietary_input = _build_dietary_input(
            record=updated,
            user_name=user_name or "Friend",
        )
        token = _DIETARY_AGENT_CONTEXT.set(
            AgentContext(
                user_id=updated.user_id,
                session_id=session_id,
                request_id=updated.request_id,
                correlation_id=updated.correlation_id or updated.candidate_id,
            )
        )
        try:
            dietary_output = await analyze_dietary_request(dietary_input)
        finally:
            _DIETARY_AGENT_CONTEXT.reset(token)
        deps.event_timeline.append(
            event_type="agent_action_proposed",
            workflow_name="meal_analysis",
            correlation_id=updated.correlation_id or updated.candidate_id,
            request_id=updated.request_id,
            user_id=updated.user_id,
            payload={
                "agent_name": "dietary_agent",
                "status": "success",
                "summary_length": len(dietary_output.analysis or ""),
            },
        )
        deps.event_timeline.append(
            event_type="dietary_agent_executed",
            workflow_name="meal_analysis",
            correlation_id=updated.correlation_id or updated.candidate_id,
            request_id=updated.request_id,
            user_id=updated.user_id,
            payload={
                "is_safe": dietary_output.is_safe,
                "warnings": dietary_output.warnings,
                "meal_name": updated.candidate_event.meal_name,
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("dietary_agent_failed error=%s candidate_id=%s", exc, updated.candidate_id)

    try:
        written = await _record_meal_memory(
            deps=deps,
            record=updated,
            session_id=session_id,
        )
        if written:
            deps.event_timeline.append(
                event_type="memory_snippet_written",
                workflow_name="meal_analysis",
                correlation_id=updated.correlation_id or updated.candidate_id,
                request_id=updated.request_id,
                user_id=updated.user_id,
                payload={
                    "meal_name": updated.candidate_event.meal_name,
                    "risk_tags": list(updated.candidate_event.risk_tags),
                },
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "meal_memory_write_failed error=%s candidate_id=%s", exc, updated.candidate_id
        )
    return updated


def _build_dietary_input(*, record: MealCandidateRecord, user_name: str) -> DietaryAgentInput:
    event = record.validated_event
    if event is None:
        raise MealCandidateInvalidStateError("candidate missing validated event")
    ingredients = [item.canonical_name for item in event.canonical_items if item.canonical_name]
    portion_size = None
    if event.canonical_items:
        estimate = event.canonical_items[0].portion_estimate
        portion_size = f"{estimate.amount} {estimate.unit}".strip()
    return DietaryAgentInput(
        user_name=user_name,
        health_goals=[],
        dietary_restrictions=[],
        meal_name=event.meal_name,
        ingredients=ingredients,
        portion_size=portion_size,
        is_safe=True,
        safety_warnings=list(record.candidate_event.risk_tags),
    )


async def _record_meal_memory(
    *, deps: MealDeps, record: MealCandidateRecord, session_id: str | None
) -> bool:
    if not deps.memory_store.enabled:
        return False
    if not session_id:
        session_id = record.candidate_id
    message = (
        f"Meal confirmed: {record.candidate_event.meal_name}. "
        f"Risks: {', '.join(record.candidate_event.risk_tags) or 'none'}. "
        f"Date: {record.captured_at.date().isoformat()}."
    )
    messages = [
        {"role": "user", "content": "Confirmed meal entry."},
        {"role": "assistant", "content": message},
    ]
    await asyncio.to_thread(
        deps.memory_store.add_messages,
        user_id=record.user_id,
        session_id=session_id,
        messages=messages,
        metadata={"source": "meal_confirmation"},
    )
    return True
