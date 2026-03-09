from __future__ import annotations

from typing import cast

from dietary_guardian.application.suggestions import (
    MissingActiveHouseholdError,
    NoMealRecordsError,
    SuggestionForbiddenError,
    SuggestionNotFoundError,
    generate_suggestion_from_report,
    get_suggestion_for_session,
    list_suggestions_for_session,
)
from dietary_guardian.application.suggestions.ports import (
    BuildUserProfileFn,
    HouseholdStorePort,
    SuggestionRepositoryPort,
)

from apps.api.dietary_api.session_profiles import build_user_profile_from_session
from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas import (
    SuggestionDetailResponse,
    SuggestionGenerateFromReportRequest,
    SuggestionGenerateFromReportResponse,
    SuggestionItemResponse,
    SuggestionListResponse,
)


def _to_suggestion_response(payload: dict[str, object]) -> SuggestionItemResponse:
    return SuggestionItemResponse.model_validate(payload)


def _raise_for_suggestions_error(exc: Exception) -> None:
    if isinstance(exc, NoMealRecordsError):
        raise build_api_error(
            status_code=400,
            code="suggestions.no_meal_records",
            message="no meal records available",
        ) from exc
    if isinstance(exc, MissingActiveHouseholdError):
        raise build_api_error(
            status_code=400,
            code="suggestions.active_household_required",
            message="active household required for household scope",
        ) from exc
    if isinstance(exc, SuggestionForbiddenError):
        raise build_api_error(
            status_code=403,
            code="suggestions.forbidden",
            message="forbidden",
        ) from exc
    if isinstance(exc, SuggestionNotFoundError):
        raise build_api_error(
            status_code=404,
            code="suggestions.not_found",
            message="suggestion not found",
        ) from exc
    raise exc


def generate_from_report(
    *,
    context: AppContext,
    session: dict[str, object],
    payload: SuggestionGenerateFromReportRequest,
    request_id: str | None,
    correlation_id: str | None,
) -> SuggestionGenerateFromReportResponse:
    def build_user_profile(session_payload: dict[str, object]):
        return build_user_profile_from_session(session_payload, context.stores.profiles)

    try:
        saved = generate_suggestion_from_report(
            repository=cast(SuggestionRepositoryPort, context.stores.recommendations),
            clinical_memory=context.clinical_memory,
            session=session,
            text=payload.text,
            request_id=request_id,
            correlation_id=correlation_id,
            build_user_profile=cast(BuildUserProfileFn, build_user_profile),
            event_timeline=context.event_timeline,
        )
    except Exception as exc:  # pragma: no cover - covered by mapped branches below
        _raise_for_suggestions_error(exc)
        raise
    return SuggestionGenerateFromReportResponse(suggestion=_to_suggestion_response(saved))


def list_for_session(
    *,
    context: AppContext,
    session: dict[str, object],
    scope: str,
    limit: int,
    source_user_id: str | None,
) -> SuggestionListResponse:
    try:
        raw_items = list_suggestions_for_session(
            repository=cast(SuggestionRepositoryPort, context.stores.recommendations),
            household_store=cast(HouseholdStorePort, context.household_store),
            session=session,
            scope=scope,
            limit=limit,
            source_user_id=source_user_id,
        )
    except Exception as exc:  # pragma: no cover
        _raise_for_suggestions_error(exc)
        raise
    return SuggestionListResponse(items=[_to_suggestion_response(item) for item in raw_items])


def get_for_session(
    *,
    context: AppContext,
    session: dict[str, object],
    scope: str,
    suggestion_id: str,
) -> SuggestionDetailResponse:
    try:
        item = get_suggestion_for_session(
            repository=cast(SuggestionRepositoryPort, context.stores.recommendations),
            household_store=cast(HouseholdStorePort, context.household_store),
            session=session,
            scope=scope,
            suggestion_id=suggestion_id,
        )
    except Exception as exc:  # pragma: no cover
        _raise_for_suggestions_error(exc)
        raise
    return SuggestionDetailResponse(suggestion=_to_suggestion_response(item))
