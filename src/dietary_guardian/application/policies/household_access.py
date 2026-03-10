"""Application module for household access."""

from __future__ import annotations

from typing import Any, Protocol


class HouseholdMembershipStorePort(Protocol):
    def get_member_role(self, household_id: str, user_id: str) -> str | None: ...

    def list_members(self, household_id: str) -> list[dict[str, Any]]: ...


class HouseholdAccessNotFoundError(Exception):
    pass


class HouseholdAccessForbiddenError(Exception):
    pass


def ensure_household_member(
    household_store: HouseholdMembershipStorePort, *, household_id: str, user_id: str
) -> str:
    role = household_store.get_member_role(household_id, user_id)
    if role is None:
        raise HouseholdAccessNotFoundError
    return role


def ensure_household_owner(
    household_store: HouseholdMembershipStorePort, *, household_id: str, user_id: str
) -> None:
    role = ensure_household_member(household_store, household_id=household_id, user_id=user_id)
    if role != "owner":
        raise HouseholdAccessForbiddenError


def household_source_members(
    household_store: HouseholdMembershipStorePort, *, household_id: str
) -> tuple[list[str], dict[str, str]]:
    members = household_store.list_members(household_id)
    source_user_ids = [str(member["user_id"]) for member in members]
    source_display_names = {
        str(member["user_id"]): str(member.get("display_name", member["user_id"])) for member in members
    }
    return source_user_ids, source_display_names
