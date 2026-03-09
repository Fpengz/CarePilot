from fastapi import APIRouter, Depends, Request

from ..routes_shared import current_session, get_context
from ..schemas import (
    DailySuggestionsResponse,
    HealthProfileEnvelopeResponse,
    HealthProfileOnboardingEnvelopeResponse,
    HealthProfileOnboardingPatchRequest,
    HealthProfileUpdateRequest,
)
from ..services.health_profiles import (
    complete_profile_onboarding,
    get_daily_suggestions,
    get_profile,
    get_profile_onboarding,
    patch_profile,
    patch_profile_onboarding,
)

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


@router.get("/api/v1/profile/health/onboarding", response_model=HealthProfileOnboardingEnvelopeResponse)
def health_profile_onboarding_get(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HealthProfileOnboardingEnvelopeResponse:
    return get_profile_onboarding(context=get_context(request), session=session)


@router.patch("/api/v1/profile/health/onboarding", response_model=HealthProfileOnboardingEnvelopeResponse)
def health_profile_onboarding_patch(
    payload: HealthProfileOnboardingPatchRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HealthProfileOnboardingEnvelopeResponse:
    return patch_profile_onboarding(context=get_context(request), session=session, payload=payload)


@router.post("/api/v1/profile/health/onboarding/complete", response_model=HealthProfileOnboardingEnvelopeResponse)
def health_profile_onboarding_complete(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HealthProfileOnboardingEnvelopeResponse:
    return complete_profile_onboarding(context=get_context(request), session=session)


@router.get("/api/v1/suggestions/daily", response_model=DailySuggestionsResponse)
def suggestions_daily(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> DailySuggestionsResponse:
    return get_daily_suggestions(context=get_context(request), session=session)
