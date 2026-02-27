from datetime import datetime, timezone
from typing import Any, TypedDict
from uuid import uuid4

from dietary_guardian.models.report import ReportInput
from dietary_guardian.safety.triage import evaluate_text_safety
from dietary_guardian.services.recommendation_service import generate_recommendation
from dietary_guardian.services.report_parser_service import build_clinical_snapshot, parse_report_input

from .ports import BuildUserProfileFn, ClinicalMemoryPort, HouseholdStorePort, SuggestionRepositoryPort

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


def _build_workflow_stub(*, request_id: str, correlation_id: str) -> dict[str, object]:
    return {
        "workflow_name": "suggestions_generate_from_report",
        "request_id": request_id,
        "correlation_id": correlation_id,
        "replayed": False,
        "timeline_events": [],
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
    if household_store.get_member_role(active_household_id, user_id) is None:
        raise SuggestionForbiddenError
    members = household_store.list_members(active_household_id)
    source_user_ids = [str(member["user_id"]) for member in members]
    source_display_names = {
        str(member["user_id"]): str(member.get("display_name", member["user_id"])) for member in members
    }
    return source_user_ids, source_display_names


def generate_suggestion_from_report(
    *,
    repository: SuggestionRepositoryPort,
    clinical_memory: ClinicalMemoryPort,
    session: dict[str, Any],
    text: str,
    request_id: str | None,
    correlation_id: str | None,
    build_user_profile: BuildUserProfileFn,
) -> dict[str, Any]:
    user_id = str(session["user_id"])
    issued_request_id = request_id or str(uuid4())
    issued_correlation_id = correlation_id or str(uuid4())
    safety = _safety_block(text)
    created_at = datetime.now(timezone.utc).isoformat()

    if safety["decision"] != "allow":
        payload: dict[str, Any] = {
            "suggestion_id": str(uuid4()),
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
            "workflow": _build_workflow_stub(request_id=issued_request_id, correlation_id=issued_correlation_id),
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

    payload = {
        "suggestion_id": str(uuid4()),
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
        "workflow": _build_workflow_stub(request_id=issued_request_id, correlation_id=issued_correlation_id),
    }
    return repository.save_suggestion_record(user_id, payload)


def list_suggestions_for_session(
    *,
    repository: SuggestionRepositoryPort,
    household_store: HouseholdStorePort,
    session: dict[str, Any],
    scope: str,
    limit: int,
) -> list[dict[str, Any]]:
    source_user_ids, source_display_names = _source_scope(scope=scope, session=session, household_store=household_store)

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
