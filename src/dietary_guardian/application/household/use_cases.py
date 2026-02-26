from dataclasses import dataclass
from typing import Any

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
    role = household_store.get_member_role(household_id, user_id)
    if role is None:
        raise HouseholdNotFoundError
    return household_store.list_members(household_id)


def create_household_invite_for_owner(
    *, household_store: HouseholdStorePort, household_id: str, user_id: str
) -> dict[str, Any]:
    role = household_store.get_member_role(household_id, user_id)
    if role is None:
        raise HouseholdNotFoundError
    if role != "owner":
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
    actor_role = household_store.get_member_role(household_id, actor_user_id)
    if actor_role is None:
        raise HouseholdNotFoundError
    if actor_role != "owner":
        raise HouseholdForbiddenError
    target_role = household_store.get_member_role(household_id, target_user_id)
    if target_role is None:
        raise HouseholdNotFoundError
    if target_role == "owner":
        raise HouseholdForbiddenError
    removed = household_store.remove_member(household_id=household_id, user_id=target_user_id)
    if not removed:
        raise HouseholdNotFoundError


def leave_household_for_member(*, household_store: HouseholdStorePort, household_id: str, user_id: str) -> None:
    role = household_store.get_member_role(household_id, user_id)
    if role is None:
        raise HouseholdNotFoundError
    if role == "owner":
        raise HouseholdOwnerLeaveForbiddenError
    removed = household_store.remove_member(household_id=household_id, user_id=user_id)
    if not removed:
        raise HouseholdNotFoundError
