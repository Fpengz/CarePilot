"""Application ports for suggestions."""

from collections.abc import Sequence
from typing import Any, Protocol

from dietary_guardian.domain.health.models import (
    BiomarkerReading,
    ClinicalProfileSnapshot,
)
from dietary_guardian.domain.identity.models import UserProfile
from dietary_guardian.domain.meals.recognition import MealRecognitionRecord


class SuggestionRepositoryPort(Protocol):
    def list_meal_records(self, user_id: str, limit: int = 20) -> list[MealRecognitionRecord]: ...
    def save_biomarker_readings(self, user_id: str, readings: list[BiomarkerReading]) -> None: ...
    def save_recommendation(self, user_id: str, payload: dict[str, Any]) -> None: ...
    def save_suggestion_record(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...
    def list_suggestion_records(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]: ...
    def get_suggestion_record(self, user_id: str, suggestion_id: str) -> dict[str, Any] | None: ...


class ClinicalMemoryPort(Protocol):
    def put(self, user_id: str, snapshot: ClinicalProfileSnapshot) -> None: ...


class EventTimelinePort(Protocol):
    def append(
        self,
        *,
        event_type: str,
        correlation_id: str,
        payload: dict[str, object],
        request_id: str | None = None,
        user_id: str | None = None,
        workflow_name: str | None = None,
    ) -> Any: ...


class HouseholdStorePort(Protocol):
    def get_member_role(self, household_id: str, user_id: str) -> str | None: ...
    def list_members(self, household_id: str) -> list[dict[str, Any]]: ...


class BuildUserProfileFn(Protocol):
    def __call__(self, session: dict[str, Any]) -> UserProfile: ...


class ParseReportFn(Protocol):
    def __call__(self, text: str) -> tuple[list[BiomarkerReading], ClinicalProfileSnapshot]: ...


class GenerateRecommendationFn(Protocol):
    def __call__(self, meal_record: MealRecognitionRecord, snapshot: ClinicalProfileSnapshot, user_profile: UserProfile) -> dict[str, Any]: ...


class EvaluateTextSafetyFn(Protocol):
    def __call__(self, text: str) -> tuple[str, Sequence[str], Sequence[str], Sequence[str]]: ...
