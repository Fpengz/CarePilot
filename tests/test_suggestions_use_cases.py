from dataclasses import dataclass, field
from typing import Any, cast

import pytest

from dietary_guardian.application.suggestions.ports import BuildUserProfileFn
from dietary_guardian.application.suggestions.use_cases import (
    MissingActiveHouseholdError,
    NoMealRecordsError,
    generate_suggestion_from_report,
    list_suggestions_for_session,
)
from dietary_guardian.models.user import MedicalCondition, Medication, UserProfile


@dataclass
class FakeRepository:
    meals: dict[str, list[Any]] = field(default_factory=dict)
    suggestions: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def list_meal_records(self, user_id: str, limit: int = 20) -> list[Any]:
        return self.meals.get(user_id, [])[:limit]

    def save_biomarker_readings(self, user_id: str, readings: list[Any]) -> None:
        return None

    def save_recommendation(self, user_id: str, payload: dict[str, Any]) -> None:
        return None

    def save_suggestion_record(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.suggestions.setdefault(user_id, []).append(payload)
        return payload

    def list_suggestion_records(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        return list(self.suggestions.get(user_id, []))[:limit]

    def get_suggestion_record(self, user_id: str, suggestion_id: str) -> dict[str, Any] | None:
        for item in self.suggestions.get(user_id, []):
            if item.get("suggestion_id") == suggestion_id:
                return item
        return None


@dataclass
class FakeClinicalMemory:
    def put(self, user_id: str, snapshot: Any) -> None:
        return None


@dataclass
class FakeHouseholdStore:
    members: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def get_member_role(self, household_id: str, user_id: str) -> str | None:
        for member in self.members.get(household_id, []):
            if member["user_id"] == user_id:
                return str(member["role"])
        return None

    def list_members(self, household_id: str) -> list[dict[str, Any]]:
        return list(self.members.get(household_id, []))


def _session(user_id: str = "user_001", display_name: str = "Member") -> dict[str, Any]:
    return {
        "user_id": user_id,
        "display_name": display_name,
        "email": f"{user_id}@example.com",
        "session_id": "s1",
        "account_role": "member",
        "profile_mode": "self",
        "scopes": ["report:write", "recommendation:generate", "report:read"],
    }


def _build_user_profile(_: dict[str, Any]) -> UserProfile:
    return UserProfile(
        id="user_001",
        name="Member",
        age=40,
        conditions=[MedicalCondition(name="Diabetes", severity="High")],
        medications=[Medication(name="Metformin", dosage="500mg")],
        profile_mode="self",
    )


def test_generate_suggestion_escalates_on_red_flag_without_meal() -> None:
    repo = FakeRepository()

    result = generate_suggestion_from_report(
        repository=repo,
        clinical_memory=FakeClinicalMemory(),
        session=_session(),
        text="I have chest pain and trouble breathing",
        request_id="req-1",
        correlation_id="corr-1",
        build_user_profile=cast(BuildUserProfileFn, _build_user_profile),  # not used in escalation path
    )

    assert result["safety"]["decision"] == "escalate"
    assert result["recommendation"]["safe"] is False
    assert result["workflow"]["request_id"] == "req-1"
    assert result["workflow"]["correlation_id"] == "corr-1"


def test_generate_suggestion_requires_meal_when_no_red_flag() -> None:
    repo = FakeRepository()

    with pytest.raises(NoMealRecordsError):
        generate_suggestion_from_report(
            repository=repo,
            clinical_memory=FakeClinicalMemory(),
            session=_session(),
            text="HbA1c 7.1 LDL 4.2",
            request_id=None,
            correlation_id=None,
            build_user_profile=cast(BuildUserProfileFn, _build_user_profile),
        )


def test_list_suggestions_household_scope_merges_members() -> None:
    repo = FakeRepository(
        suggestions={
            "user_001": [{"suggestion_id": "s1", "created_at": "2026-01-01T00:00:00+00:00"}],
            "care_001": [{"suggestion_id": "s2", "created_at": "2026-01-02T00:00:00+00:00"}],
        }
    )
    households = FakeHouseholdStore(
        members={
            "hh_1": [
                {"user_id": "user_001", "display_name": "Member", "role": "owner"},
                {"user_id": "care_001", "display_name": "Helper", "role": "member"},
            ]
        }
    )
    session = _session()
    session["active_household_id"] = "hh_1"

    items = list_suggestions_for_session(
        repository=repo,
        household_store=households,
        session=session,
        scope="household",
        limit=20,
    )

    assert [item["suggestion_id"] for item in items] == ["s2", "s1"]
    assert {item["source_user_id"] for item in items} == {"user_001", "care_001"}


def test_list_suggestions_household_scope_requires_active_household() -> None:
    with pytest.raises(MissingActiveHouseholdError):
        list_suggestions_for_session(
            repository=FakeRepository(),
            household_store=FakeHouseholdStore(),
            session=_session(),
            scope="household",
            limit=20,
        )
