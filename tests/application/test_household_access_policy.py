"""Tests for household access policy."""

from dataclasses import dataclass, field
from typing import Any

import pytest

from dietary_guardian.application.policies.household_access import (
    HouseholdAccessForbiddenError,
    HouseholdAccessNotFoundError,
    ensure_household_member,
    ensure_household_owner,
    household_source_members,
)


@dataclass
class FakeHouseholdStore:
    members: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def get_member_role(self, household_id: str, user_id: str) -> str | None:
        for item in self.members.get(household_id, []):
            if item["user_id"] == user_id:
                return str(item["role"])
        return None

    def list_members(self, household_id: str) -> list[dict[str, Any]]:
        return list(self.members.get(household_id, []))


def test_ensure_household_member_returns_role_for_member() -> None:
    store = FakeHouseholdStore(
        members={"hh_1": [{"user_id": "user_001", "display_name": "Alex", "role": "owner"}]}
    )

    role = ensure_household_member(store, household_id="hh_1", user_id="user_001")

    assert role == "owner"


def test_ensure_household_member_raises_not_found_for_non_member() -> None:
    store = FakeHouseholdStore(members={"hh_1": [{"user_id": "user_001", "display_name": "Alex", "role": "owner"}]})

    with pytest.raises(HouseholdAccessNotFoundError):
        ensure_household_member(store, household_id="hh_1", user_id="care_001")


def test_ensure_household_owner_raises_forbidden_for_non_owner() -> None:
    store = FakeHouseholdStore(
        members={"hh_1": [{"user_id": "care_001", "display_name": "Casey", "role": "member"}]}
    )

    with pytest.raises(HouseholdAccessForbiddenError):
        ensure_household_owner(store, household_id="hh_1", user_id="care_001")


def test_household_source_members_returns_ids_and_display_names() -> None:
    store = FakeHouseholdStore(
        members={
            "hh_1": [
                {"user_id": "user_001", "display_name": "Alex", "role": "owner"},
                {"user_id": "care_001", "display_name": "Casey", "role": "member"},
            ]
        }
    )

    ids, names = household_source_members(store, household_id="hh_1")

    assert ids == ["user_001", "care_001"]
    assert names == {"user_001": "Alex", "care_001": "Casey"}
