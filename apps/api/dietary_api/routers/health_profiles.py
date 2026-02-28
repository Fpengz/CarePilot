from fastapi import APIRouter, Depends, Request

from ..routes_shared import current_session, get_context
from ..schemas import DailySuggestionsResponse, HealthProfileEnvelopeResponse, HealthProfileUpdateRequest
from ..services.health_profiles import get_daily_suggestions, get_profile, patch_profile

router = APIRouter(tags=["health-profile"])


@router.get("/api/v1/profile/health", response_model=HealthProfileEnvelopeResponse)
def health_profile_get(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HealthProfileEnvelopeResponse:
    return get_profile(context=get_context(request), session=session)


@router.patch("/api/v1/profile/health", response_model=HealthProfileEnvelopeResponse)
def health_profile_patch(
    payload: HealthProfileUpdateRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HealthProfileEnvelopeResponse:
    return patch_profile(context=get_context(request), session=session, payload=payload)


@router.get("/api/v1/suggestions/daily", response_model=DailySuggestionsResponse)
def suggestions_daily(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> DailySuggestionsResponse:
    return get_daily_suggestions(context=get_context(request), session=session)
