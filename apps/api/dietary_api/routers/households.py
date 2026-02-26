from datetime import datetime
from typing import Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Request

from dietary_guardian.application.household import (
    HouseholdAlreadyExistsError,
    HouseholdForbiddenError,
    HouseholdInviteInvalidError,
    HouseholdMembershipConflictError,
    HouseholdNotFoundError,
    create_household_for_user,
    create_household_invite_for_owner,
    get_current_household_bundle,
    join_household_by_code,
    list_household_members_for_user,
)

from ..routes_shared import current_session, get_context
from ..schemas import (
    HouseholdBundleResponse,
    HouseholdCreateRequest,
    HouseholdInviteCreateResponse,
    HouseholdInviteResponseItem,
    HouseholdJoinRequest,
    HouseholdMemberItem,
    HouseholdMembersResponse,
    HouseholdResponse,
)

router = APIRouter(tags=["households"])


def _household_response(item: dict[str, object]) -> HouseholdResponse:
    return HouseholdResponse(
        household_id=str(item["household_id"]),
        name=str(item["name"]),
        owner_user_id=str(item["owner_user_id"]),
        created_at=datetime.fromisoformat(str(item["created_at"])),
    )


def _member_response(item: dict[str, object]) -> HouseholdMemberItem:
    return HouseholdMemberItem(
        user_id=str(item["user_id"]),
        display_name=str(item["display_name"]),
        role=cast(Literal["owner", "member"], item["role"]),
        joined_at=datetime.fromisoformat(str(item["joined_at"])),
    )


def _bundle_response(bundle_household: dict[str, object] | None, members: list[dict[str, object]]) -> HouseholdBundleResponse:
    return HouseholdBundleResponse(
        household=(_household_response(bundle_household) if bundle_household is not None else None),
        members=[_member_response(item) for item in members],
    )


@router.post("/api/v1/households", response_model=HouseholdBundleResponse)
def create_household(
    payload: HouseholdCreateRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HouseholdBundleResponse:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="household name must not be blank")
    ctx = get_context(request)
    try:
        bundle = create_household_for_user(
            household_store=ctx.household_store,
            user_id=str(session["user_id"]),
            display_name=str(session["display_name"]),
            name=name,
        )
    except HouseholdAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail="user already belongs to a household") from exc
    return _bundle_response(bundle.household, bundle.members)


@router.get("/api/v1/households/current", response_model=HouseholdBundleResponse)
def get_current_household(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HouseholdBundleResponse:
    ctx = get_context(request)
    bundle = get_current_household_bundle(household_store=ctx.household_store, user_id=str(session["user_id"]))
    return _bundle_response(bundle.household, bundle.members)


@router.get("/api/v1/households/{household_id}/members", response_model=HouseholdMembersResponse)
def list_household_members(
    household_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HouseholdMembersResponse:
    ctx = get_context(request)
    try:
        members = list_household_members_for_user(
            household_store=ctx.household_store,
            household_id=household_id,
            user_id=str(session["user_id"]),
        )
    except HouseholdNotFoundError as exc:
        raise HTTPException(status_code=404, detail="household not found") from exc
    return HouseholdMembersResponse(members=[_member_response(item) for item in members])


@router.post("/api/v1/households/{household_id}/invites", response_model=HouseholdInviteCreateResponse)
def create_household_invite(
    household_id: str,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HouseholdInviteCreateResponse:
    ctx = get_context(request)
    try:
        invite = create_household_invite_for_owner(
            household_store=ctx.household_store,
            household_id=household_id,
            user_id=str(session["user_id"]),
        )
    except HouseholdNotFoundError as exc:
        raise HTTPException(status_code=404, detail="household not found") from exc
    except HouseholdForbiddenError as exc:
        raise HTTPException(status_code=403, detail="forbidden") from exc
    return HouseholdInviteCreateResponse(
        invite=HouseholdInviteResponseItem(
            invite_id=str(invite["invite_id"]),
            household_id=str(invite["household_id"]),
            code=str(invite["code"]),
            created_by_user_id=str(invite["created_by_user_id"]),
            created_at=datetime.fromisoformat(str(invite["created_at"])),
            expires_at=datetime.fromisoformat(str(invite["expires_at"])),
            max_uses=int(invite["max_uses"]),
            uses=int(invite["uses"]),
        )
    )


@router.post("/api/v1/households/join", response_model=HouseholdBundleResponse)
def join_household(
    payload: HouseholdJoinRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> HouseholdBundleResponse:
    ctx = get_context(request)
    try:
        bundle = join_household_by_code(
            household_store=ctx.household_store,
            code=payload.code.strip(),
            user_id=str(session["user_id"]),
            display_name=str(session["display_name"]),
        )
    except HouseholdMembershipConflictError as exc:
        raise HTTPException(status_code=409, detail="user already belongs to a household") from exc
    except HouseholdInviteInvalidError as exc:
        raise HTTPException(status_code=400, detail="invalid household invite") from exc
    return _bundle_response(bundle.household, bundle.members)
