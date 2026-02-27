from dataclasses import dataclass
from typing import Any

from dietary_guardian.application.policies.household_access import (
    HouseholdAccessForbiddenError,
    HouseholdAccessNotFoundError,
    ensure_household_member,
    ensure_household_owner,
)

from .ports import HouseholdStorePort


class HouseholdAlreadyExistsError(Exception):
    pass


class HouseholdNotFoundError(Exception):
    pass


class HouseholdForbiddenError(Exception):
    pass


class HouseholdInviteInvalidError(Exception):
    pass


class HouseholdMembershipConflictError(Exception):
    pass


class HouseholdOwnerLeaveForbiddenError(Exception):
    pass


@dataclass
class HouseholdBundle:
    household: dict[str, Any] | None
    members: list[dict[str, Any]]


@dataclass
class HouseholdInviteResult:
    household: dict[str, Any]
    invite: dict[str, Any]


def get_current_household_bundle(*, household_store: HouseholdStorePort, user_id: str) -> HouseholdBundle:
    household = household_store.get_household_for_user(user_id)
    if household is None:
        return HouseholdBundle(household=None, members=[])
    return HouseholdBundle(household=household, members=household_store.list_members(str(household["household_id"])))


def create_household_for_user(
    *,
    household_store: HouseholdStorePort,
    user_id: str,
    display_name: str,
    name: str,
) -> HouseholdBundle:
    if household_store.get_household_for_user(user_id) is not None:
        raise HouseholdAlreadyExistsError
    household = household_store.create_household(
        owner_user_id=user_id,
        owner_display_name=display_name,
        name=name,
    )
    return HouseholdBundle(household=household, members=household_store.list_members(str(household["household_id"])))


def list_household_members_for_user(
    *, household_store: HouseholdStorePort, household_id: str, user_id: str
) -> list[dict[str, Any]]:
    try:
        ensure_household_member(household_store, household_id=household_id, user_id=user_id)
    except HouseholdAccessNotFoundError:
        raise HouseholdNotFoundError
    return household_store.list_members(household_id)


def create_household_invite_for_owner(
    *, household_store: HouseholdStorePort, household_id: str, user_id: str
) -> dict[str, Any]:
    try:
        ensure_household_owner(household_store, household_id=household_id, user_id=user_id)
    except HouseholdAccessNotFoundError:
        raise HouseholdNotFoundError
    except HouseholdAccessForbiddenError:
        raise HouseholdForbiddenError
    return household_store.create_invite(household_id=household_id, created_by_user_id=user_id)


def join_household_by_code(
    *,
    household_store: HouseholdStorePort,
    code: str,
    user_id: str,
    display_name: str,
) -> HouseholdBundle:
    if household_store.get_household_for_user(user_id) is not None:
        raise HouseholdMembershipConflictError
    result = household_store.join_by_invite(code=code, user_id=user_id, display_name=display_name)
    if result is None:
        raise HouseholdInviteInvalidError
    household, joined = result
    if not joined:
        raise HouseholdMembershipConflictError
    return HouseholdBundle(household=household, members=household_store.list_members(str(household["household_id"])))


def remove_household_member_for_owner(
    *, household_store: HouseholdStorePort, household_id: str, actor_user_id: str, target_user_id: str
) -> None:
    try:
        ensure_household_owner(household_store, household_id=household_id, user_id=actor_user_id)
    except HouseholdAccessNotFoundError:
        raise HouseholdNotFoundError
    except HouseholdAccessForbiddenError:
        raise HouseholdForbiddenError
    try:
        target_role = ensure_household_member(
            household_store, household_id=household_id, user_id=target_user_id
        )
    except HouseholdAccessNotFoundError:
        raise HouseholdNotFoundError
    if target_role == "owner":
        raise HouseholdForbiddenError
    removed = household_store.remove_member(household_id=household_id, user_id=target_user_id)
    if not removed:
        raise HouseholdNotFoundError


def leave_household_for_member(*, household_store: HouseholdStorePort, household_id: str, user_id: str) -> None:
    try:
        role = ensure_household_member(household_store, household_id=household_id, user_id=user_id)
    except HouseholdAccessNotFoundError:
        raise HouseholdNotFoundError
    if role == "owner":
        raise HouseholdOwnerLeaveForbiddenError
    removed = household_store.remove_member(household_id=household_id, user_id=user_id)
    if not removed:
        raise HouseholdNotFoundError


def rename_household_for_owner(
    *, household_store: HouseholdStorePort, household_id: str, actor_user_id: str, name: str
) -> HouseholdBundle:
    try:
        ensure_household_owner(household_store, household_id=household_id, user_id=actor_user_id)
    except HouseholdAccessNotFoundError:
        raise HouseholdNotFoundError
    except HouseholdAccessForbiddenError:
        raise HouseholdForbiddenError
    household = household_store.rename_household(household_id=household_id, name=name)
    if household is None:
        raise HouseholdNotFoundError
    return HouseholdBundle(household=household, members=household_store.list_members(household_id))


def validate_active_household_for_user(
    *, household_store: HouseholdStorePort, household_id: str | None, user_id: str
) -> str | None:
    if household_id is None:
        return None
    try:
        ensure_household_member(household_store, household_id=household_id, user_id=user_id)
    except HouseholdAccessNotFoundError:
        raise HouseholdNotFoundError
    return household_id
