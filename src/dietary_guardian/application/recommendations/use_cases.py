"""Application use cases for recommendations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict
from uuid import uuid4

from apps.api.dietary_api.deps import RecommendationAgentDeps, RecommendationDeps
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas import (
    RecommendationAgentResponse,
    RecommendationGenerateResponse,
    RecommendationInteractionRequest,
    RecommendationInteractionResponse,
    RecommendationSubstitutionRequest,
    RecommendationSubstitutionResponse,
    WorkflowResponse,
)
from dietary_guardian.application.auth.session_context import build_user_profile_from_session
from dietary_guardian.application.policies.household_access import (
    HouseholdAccessNotFoundError,
    ensure_household_member,
    household_source_members,
)
from dietary_guardian.capabilities.schemas import RecommendationAgentInput
from dietary_guardian.domain.health.models import ReportInput
from dietary_guardian.domain.profiles.health_profile import resolve_user_profile
from dietary_guardian.domain.recommendations.engine import (
    AgentMealNotFoundError,
    build_substitution_plan,
    record_interaction_and_update_preferences,
)
from dietary_guardian.domain.recommendations.meal_recommendations import generate_recommendation
from dietary_guardian.domain.reports import build_clinical_snapshot, parse_report_input
from dietary_guardian.domain.safety.triage import evaluate_text_safety

from .ports import (
    BuildUserProfileFn,
    ClinicalMemoryPort,
    EventTimelinePort,
    HouseholdStorePort,
    SuggestionRepositoryPort,
)

SUGGESTION_DISCLAIMER = (
    "This information is for general wellness and care support only, not a diagnosis. "
    "If symptoms are severe, worsening, or concerning, seek urgent medical care."
)


class SafetyBlock(TypedDict):
    decision: str
    reasons: list[str]
    required_actions: list[str]
    redactions: list[str]


class NoMealRecordsError(Exception):
    pass


class MissingActiveHouseholdError(Exception):
    pass


class SuggestionForbiddenError(Exception):
    pass


class SuggestionNotFoundError(Exception):
    pass


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event_to_json(event: object) -> dict[str, object]:
    if hasattr(event, "model_dump"):
        return dict(getattr(event, "model_dump")(mode="json"))
    if isinstance(event, dict):
        return {str(k): v for k, v in event.items()}
    return {"event_type": "unknown"}


def _build_workflow_with_timeline(*, request_id: str, correlation_id: str, events: list[dict[str, object]]) -> dict[str, object]:
    return {
        "workflow_name": "suggestions_generate_from_report",
        "request_id": request_id,
        "correlation_id": correlation_id,
        "replayed": False,
        "timeline_events": events,
    }


def _safety_block(text: str) -> SafetyBlock:
    decision = evaluate_text_safety(text)
    return {
        "decision": decision.decision,
        "reasons": list(decision.reasons),
        "required_actions": list(decision.required_actions),
        "redactions": list(decision.redactions),
    }


def _source_scope(
    *,
    scope: str,
    session: dict[str, Any],
    household_store: HouseholdStorePort,
) -> tuple[list[str], dict[str, str]]:
    user_id = str(session["user_id"])
    if scope == "self":
        return [user_id], {user_id: str(session["display_name"])}

    active_household_id = session.get("active_household_id")
    if not isinstance(active_household_id, str) or not active_household_id:
        raise MissingActiveHouseholdError
    try:
        ensure_household_member(household_store, household_id=active_household_id, user_id=user_id)
    except HouseholdAccessNotFoundError:
        raise SuggestionForbiddenError
    return household_source_members(household_store, household_id=active_household_id)


def generate_suggestion_from_report(
    *,
    repository: SuggestionRepositoryPort,
    clinical_memory: ClinicalMemoryPort,
    session: dict[str, Any],
    text: str,
    request_id: str | None,
    correlation_id: str | None,
    build_user_profile: BuildUserProfileFn,
    event_timeline: EventTimelinePort | None = None,
) -> dict[str, Any]:
    user_id = str(session["user_id"])
    issued_request_id = request_id or str(uuid4())
    issued_correlation_id = correlation_id or str(uuid4())
    safety = _safety_block(text)
    created_at = _iso_now()
    suggestion_id = str(uuid4())
    timeline_events: list[dict[str, object]] = []

    if event_timeline is not None:
        started = event_timeline.append(
            event_type="workflow_started",
            workflow_name="suggestions_generate_from_report",
            request_id=issued_request_id,
            correlation_id=issued_correlation_id,
            user_id=user_id,
            payload={"safety_decision": str(safety["decision"]), "suggestion_id": suggestion_id},
        )
        timeline_events.append(_event_to_json(started))

    if safety["decision"] != "allow":
        if event_timeline is not None:
            escalated = event_timeline.append(
                event_type="workflow_escalated",
                workflow_name="suggestions_generate_from_report",
                request_id=issued_request_id,
                correlation_id=issued_correlation_id,
                user_id=user_id,
                payload={"safety_decision": str(safety["decision"]), "suggestion_id": suggestion_id},
            )
            timeline_events.append(_event_to_json(escalated))
        payload: dict[str, Any] = {
            "suggestion_id": suggestion_id,
            "created_at": created_at,
            "source_user_id": user_id,
            "source_display_name": str(session["display_name"]),
            "disclaimer": SUGGESTION_DISCLAIMER,
            "safety": safety,
            "report_parse": {"readings": [], "snapshot": {"biomarkers": {}, "risk_flags": []}},
            "recommendation": {
                "safe": False,
                "rationale": "Red-flag symptoms detected. Seek urgent medical care immediately.",
                "localized_advice": list(safety["required_actions"]),
                "blocked_reason": "red_flag_escalation",
                "evidence": {},
            },
            "workflow": _build_workflow_with_timeline(request_id=issued_request_id, correlation_id=issued_correlation_id, events=timeline_events),
        }
        return repository.save_suggestion_record(user_id, payload)

    meal_records = repository.list_meal_records(user_id)
    if not meal_records:
        raise NoMealRecordsError

    readings = parse_report_input(ReportInput(source="pasted_text", text=text))
    snapshot = build_clinical_snapshot(readings)
    repository.save_biomarker_readings(user_id, readings)
    clinical_memory.put(user_id, snapshot)

    user_profile = build_user_profile(session)
    recommendation = generate_recommendation(meal_records[-1], snapshot, user_profile)
    recommendation_json = recommendation.model_dump(mode="json")
    repository.save_recommendation(user_id, recommendation_json)

    if event_timeline is not None:
        completed = event_timeline.append(
            event_type="workflow_completed",
            workflow_name="suggestions_generate_from_report",
            request_id=issued_request_id,
            correlation_id=issued_correlation_id,
            user_id=user_id,
            payload={
                "safety_decision": str(safety["decision"]),
                "reading_count": len(readings),
                "suggestion_id": suggestion_id,
            },
        )
        timeline_events.append(_event_to_json(completed))

    payload = {
        "suggestion_id": suggestion_id,
        "created_at": created_at,
        "source_user_id": user_id,
        "source_display_name": str(session["display_name"]),
        "disclaimer": SUGGESTION_DISCLAIMER,
        "safety": safety,
        "report_parse": {
            "readings": [item.model_dump(mode="json") for item in readings],
            "snapshot": snapshot.model_dump(mode="json"),
        },
        "recommendation": recommendation_json,
        "workflow": _build_workflow_with_timeline(request_id=issued_request_id, correlation_id=issued_correlation_id, events=timeline_events),
    }
    return repository.save_suggestion_record(user_id, payload)


def list_suggestions_for_session(
    *,
    repository: SuggestionRepositoryPort,
    household_store: HouseholdStorePort,
    session: dict[str, Any],
    scope: str,
    limit: int,
    source_user_id: str | None = None,
) -> list[dict[str, Any]]:
    source_user_ids, source_display_names = _source_scope(scope=scope, session=session, household_store=household_store)
    if source_user_id is not None:
        if source_user_id not in source_user_ids:
            raise SuggestionForbiddenError
        source_user_ids = [source_user_id]

    raw_items: list[dict[str, Any]] = []
    for source_user_id in source_user_ids:
        for item in repository.list_suggestion_records(source_user_id, limit=limit):
            normalized = dict(item)
            normalized.setdefault("source_user_id", source_user_id)
            normalized.setdefault("source_display_name", source_display_names.get(source_user_id, source_user_id))
            raw_items.append(normalized)
    raw_items.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return raw_items[:limit]


def get_suggestion_for_session(
    *,
    repository: SuggestionRepositoryPort,
    household_store: HouseholdStorePort,
    session: dict[str, Any],
    scope: str,
    suggestion_id: str,
) -> dict[str, Any]:
    source_user_ids, source_display_names = _source_scope(scope=scope, session=session, household_store=household_store)

    for source_user_id in source_user_ids:
        found = repository.get_suggestion_record(source_user_id, suggestion_id)
        if found is not None:
            normalized = dict(found)
            normalized.setdefault("source_user_id", source_user_id)
            normalized.setdefault("source_display_name", source_display_names.get(source_user_id, source_user_id))
            return normalized
    raise SuggestionNotFoundError


# ---------------------------------------------------------------------------
# Clinical-snapshot helper (shared across recommendation flows)
# ---------------------------------------------------------------------------

def _resolve_clinical_snapshot(*, deps: Any, user_id: str) -> Any:
    """Resolve the clinical snapshot from cache or by rebuilding from biomarker readings."""
    snapshot = deps.clinical_memory.get(user_id)
    if snapshot is not None:
        return snapshot
    readings = deps.stores.biomarkers.list_biomarker_readings(user_id)
    if not readings:
        return None
    snapshot = build_clinical_snapshot(readings)
    deps.clinical_memory.put(user_id, snapshot)
    return snapshot


# ---------------------------------------------------------------------------
# Single-record recommendation flow
# ---------------------------------------------------------------------------

def generate_recommendation_for_session(
    *,
    deps: RecommendationDeps,
    session: dict[str, object],
    request_id: str | None,
    correlation_id: str | None,
) -> RecommendationGenerateResponse:
    user_id = str(session["user_id"])
    meal_records = deps.stores.meals.list_meal_records(user_id)
    if not meal_records:
        raise build_api_error(
            status_code=400,
            code="recommendations.no_meal_records",
            message="no meal records available",
        )

    snapshot = deps.clinical_memory.get(user_id)
    if snapshot is None:
        readings = deps.stores.biomarkers.list_biomarker_readings(user_id)
        if not readings:
            raise build_api_error(
                status_code=400,
                code="recommendations.no_clinical_snapshot",
                message="no clinical snapshot available",
            )
        snapshot = build_clinical_snapshot(readings)
        deps.clinical_memory.put(user_id, snapshot)

    user_profile = build_user_profile_from_session(session, deps.stores.profiles)
    recommendation = generate_recommendation(meal_records[-1], snapshot, user_profile)
    recommendation_json = recommendation.model_dump(mode="json")
    deps.stores.recommendations.save_recommendation(user_id, recommendation_json)

    workflow = {
        "workflow_name": "recommendation_generate",
        "request_id": str(request_id or ""),
        "correlation_id": str(correlation_id or ""),
        "replayed": False,
        "timeline_events": [],
    }
    return RecommendationGenerateResponse(
        recommendation=recommendation,
        workflow=WorkflowResponse.model_validate(workflow),
    )


# ---------------------------------------------------------------------------
# Agent-based daily plan flows
# ---------------------------------------------------------------------------

def get_daily_agent_for_session(
    *,
    deps: RecommendationAgentDeps,
    session: dict[str, object],
    request_id: str | None,
    correlation_id: str | None,
) -> RecommendationAgentResponse:
    user_id = str(session["user_id"])
    health_profile, user_profile = resolve_user_profile(deps.stores.profiles, session)
    meal_history = deps.stores.meals.list_meal_records(user_id)
    clinical_snapshot = _resolve_clinical_snapshot(deps=deps, user_id=user_id)
    output = deps.recommendation_agent.generate(
        RecommendationAgentInput(
            user_id=user_id,
            health_profile=health_profile,
            user_profile=user_profile,
            meal_history=meal_history,
            clinical_snapshot=clinical_snapshot,
        ),
        repository=deps.stores.recommendations,
    )
    recommendation = output.recommendation
    payload = recommendation.model_dump(mode="json")
    payload["workflow"] = {
        "workflow_name": "daily_recommendation_agent",
        "request_id": str(request_id or ""),
        "correlation_id": str(correlation_id or ""),
        "replayed": False,
        "timeline_events": [],
    }
    return RecommendationAgentResponse.model_validate(payload)


def get_substitutions_for_session(
    *,
    deps: RecommendationAgentDeps,
    session: dict[str, object],
    payload: RecommendationSubstitutionRequest,
) -> RecommendationSubstitutionResponse:
    user_id = str(session["user_id"])
    health_profile, user_profile = resolve_user_profile(deps.stores.profiles, session)
    meal_history = deps.stores.meals.list_meal_records(user_id)
    clinical_snapshot = _resolve_clinical_snapshot(deps=deps, user_id=user_id)
    try:
        plan = build_substitution_plan(
            repository=deps.stores.recommendations,
            user_id=user_id,
            health_profile=health_profile,
            user_profile=user_profile,
            meal_history=meal_history,
            clinical_snapshot=clinical_snapshot,
            source_meal_id=payload.source_meal_id,
            limit=payload.limit,
        )
    except AgentMealNotFoundError as exc:
        raise build_api_error(
            status_code=404,
            code="recommendations.meal_not_found",
            message="meal record not found",
            details={"meal_id": str(exc)},
        ) from exc
    if plan is None:
        raise build_api_error(
            status_code=400,
            code="recommendations.no_meal_records",
            message="no meal records available",
        )
    return RecommendationSubstitutionResponse.model_validate(plan.model_dump(mode="json"))


def record_interaction_for_session(
    *,
    deps: RecommendationAgentDeps,
    session: dict[str, object],
    payload: RecommendationInteractionRequest,
) -> RecommendationInteractionResponse:
    user_id = str(session["user_id"])
    meal_history = deps.stores.meals.list_meal_records(user_id)
    try:
        interaction, snapshot = record_interaction_and_update_preferences(
            repository=deps.stores.recommendations,
            user_id=user_id,
            candidate_id=payload.candidate_id,
            recommendation_id=payload.recommendation_id,
            event_type=payload.event_type,
            slot=payload.slot,
            source_meal_id=payload.source_meal_id,
            selected_meal_id=payload.selected_meal_id,
            metadata=payload.metadata,
            meal_history=meal_history,
        )
    except AgentMealNotFoundError as exc:
        raise build_api_error(
            status_code=404,
            code="recommendations.candidate_not_found",
            message="candidate not found",
            details={"candidate_id": str(exc)},
        ) from exc
    return RecommendationInteractionResponse(
        interaction=interaction.model_dump(mode="json"),
        preference_snapshot=snapshot.model_dump(mode="json"),
    )
