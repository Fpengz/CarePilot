from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class MealStore:
    _store: Any

    def save_meal_record(self, record: Any) -> None:
        self._store.save_meal_record(record)

    def list_meal_records(self, user_id: str) -> list[Any]:
        return self._store.list_meal_records(user_id)

    def get_meal_record(self, user_id: str, meal_id: str) -> Any | None:
        return self._store.get_meal_record(user_id, meal_id)

    def list_meal_catalog_items(self, *, locale: str, slot: str | None = None, limit: int = 100) -> list[Any]:
        return self._store.list_meal_catalog_items(locale=locale, slot=slot, limit=limit)

    def get_meal_catalog_item(self, meal_id: str) -> Any | None:
        return self._store.get_meal_catalog_item(meal_id)


@dataclass(slots=True)
class BiomarkerStore:
    _store: Any

    def save_biomarker_readings(self, user_id: str, readings: list[Any]) -> None:
        self._store.save_biomarker_readings(user_id, readings)

    def list_biomarker_readings(self, user_id: str) -> list[Any]:
        return self._store.list_biomarker_readings(user_id)


@dataclass(slots=True)
class SymptomStore:
    _store: Any

    def save_symptom_checkin(self, checkin: Any) -> Any:
        return self._store.save_symptom_checkin(checkin)

    def list_symptom_checkins(
        self,
        *,
        user_id: str,
        start_at: Any | None = None,
        end_at: Any | None = None,
        limit: int = 100,
    ) -> list[Any]:
        return self._store.list_symptom_checkins(
            user_id=user_id,
            start_at=start_at,
            end_at=end_at,
            limit=limit,
        )


@dataclass(slots=True)
class MedicationStore:
    _store: Any

    def list_medication_regimens(self, user_id: str, *, active_only: bool = False) -> list[Any]:
        return self._store.list_medication_regimens(user_id, active_only=active_only)

    def save_medication_regimen(self, regimen: Any) -> None:
        self._store.save_medication_regimen(regimen)

    def get_medication_regimen(self, *, user_id: str, regimen_id: str) -> Any | None:
        return self._store.get_medication_regimen(user_id=user_id, regimen_id=regimen_id)

    def delete_medication_regimen(self, *, user_id: str, regimen_id: str) -> bool:
        return self._store.delete_medication_regimen(user_id=user_id, regimen_id=regimen_id)

    def save_medication_adherence_event(self, event: Any) -> Any:
        return self._store.save_medication_adherence_event(event)

    def list_medication_adherence_events(
        self,
        *,
        user_id: str,
        start_at: Any | None = None,
        end_at: Any | None = None,
        limit: int = 200,
    ) -> list[Any]:
        items = self._store.list_medication_adherence_events(
            user_id=user_id,
            start_at=start_at,
            end_at=end_at,
        )
        return items[:limit]


@dataclass(slots=True)
class ReminderStore:
    _store: Any

    def save_reminder_event(self, event: Any) -> None:
        self._store.save_reminder_event(event)

    def get_reminder_event(self, event_id: str) -> Any | None:
        return self._store.get_reminder_event(event_id)

    def list_reminder_events(self, user_id: str) -> list[Any]:
        return self._store.list_reminder_events(user_id)

    def list_reminder_notification_preferences(
        self,
        *,
        user_id: str,
        scope_type: str | None = None,
        scope_key: str | None = None,
        reminder_type: str | None = None,
    ) -> list[Any]:
        resolved_scope_type = scope_type
        resolved_scope_key = scope_key
        if reminder_type is not None and resolved_scope_type is None:
            resolved_scope_type = "reminder_type"
            resolved_scope_key = reminder_type
        return self._store.list_reminder_notification_preferences(
            user_id=user_id,
            scope_type=resolved_scope_type,
            scope_key=resolved_scope_key,
        )

    def replace_reminder_notification_preferences(
        self,
        *,
        user_id: str,
        scope_type: str | None = None,
        scope_key: str | None = None,
        preferences: list[Any],
    ) -> list[Any]:
        return self._store.replace_reminder_notification_preferences(
            user_id=user_id,
            scope_type=scope_type,
            scope_key=scope_key,
            preferences=preferences,
        )

    def list_scheduled_notifications(
        self,
        *,
        reminder_id: str | None = None,
        user_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[Any]:
        items = self._store.list_scheduled_notifications(
            reminder_id=reminder_id,
            user_id=user_id,
        )
        if status is not None:
            items = [item for item in items if getattr(item, "status", None) == status]
        return items[:limit]

    def list_reminder_notification_endpoints(self, *, user_id: str) -> list[Any]:
        return self._store.list_reminder_notification_endpoints(user_id=user_id)

    def replace_reminder_notification_endpoints(self, *, user_id: str, endpoints: list[Any]) -> list[Any]:
        return self._store.replace_reminder_notification_endpoints(user_id=user_id, endpoints=endpoints)

    def list_notification_logs(
        self,
        *,
        reminder_id: str | None = None,
        scheduled_notification_id: str | None = None,
        channel: str | None = None,
        limit: int = 200,
    ) -> list[Any]:
        items = self._store.list_notification_logs(
            reminder_id=reminder_id,
            scheduled_notification_id=scheduled_notification_id,
        )
        if channel is not None:
            items = [item for item in items if getattr(item, "channel", None) == channel]
        return items[:limit]

    def get_mobility_reminder_settings(self, user_id: str) -> Any | None:
        return self._store.get_mobility_reminder_settings(user_id)

    def save_mobility_reminder_settings(self, settings: Any) -> Any:
        return self._store.save_mobility_reminder_settings(settings)


@dataclass(slots=True)
class ClinicalCardStore:
    _store: Any

    def save_clinical_card(self, card: Any) -> Any:
        return self._store.save_clinical_card(card)

    def list_clinical_cards(self, *, user_id: str, limit: int = 50) -> list[Any]:
        return self._store.list_clinical_cards(user_id=user_id, limit=limit)

    def get_clinical_card(self, *, user_id: str, card_id: str) -> Any | None:
        return self._store.get_clinical_card(user_id=user_id, card_id=card_id)


@dataclass(slots=True)
class WorkflowStore:
    _store: Any

    def list_tool_role_policies(
        self,
        *,
        role: str | None = None,
        agent_id: str | None = None,
        tool_name: str | None = None,
        enabled_only: bool = False,
    ) -> list[Any]:
        return self._store.list_tool_role_policies(
            role=role,
            agent_id=agent_id,
            tool_name=tool_name,
            enabled_only=enabled_only,
        )

    def save_tool_role_policy(self, record: Any) -> Any:
        return self._store.save_tool_role_policy(record)

    def get_tool_role_policy(self, policy_id: str) -> Any | None:
        return self._store.get_tool_role_policy(policy_id)

    def save_workflow_contract_snapshot(self, snapshot: Any) -> Any:
        return self._store.save_workflow_contract_snapshot(snapshot)

    def list_workflow_contract_snapshots(self, *, limit: int = 50) -> list[Any]:
        return self._store.list_workflow_contract_snapshots(limit=limit)

    def get_workflow_contract_snapshot(self, *, version: int) -> Any | None:
        return self._store.get_workflow_contract_snapshot(version=version)

    def supports_contract_snapshots(self) -> bool:
        return hasattr(self._store, "list_workflow_contract_snapshots") and hasattr(
            self._store,
            "save_workflow_contract_snapshot",
        )


@dataclass(slots=True)
class RecommendationStore:
    _store: Any

    def save_recommendation(self, user_id: str, payload: dict[str, Any]) -> None:
        self._store.save_recommendation(user_id, payload)

    def save_recommendation_interaction(self, interaction: Any) -> Any:
        return self._store.save_recommendation_interaction(interaction)

    def list_recommendation_interactions(self, user_id: str, *, limit: int = 200) -> list[Any]:
        return self._store.list_recommendation_interactions(user_id, limit=limit)

    def get_preference_snapshot(self, user_id: str) -> Any | None:
        return self._store.get_preference_snapshot(user_id)

    def save_preference_snapshot(self, snapshot: Any) -> Any:
        return self._store.save_preference_snapshot(snapshot)

    def save_suggestion_record(self, user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._store.save_suggestion_record(user_id, payload)

    def list_suggestion_records(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._store.list_suggestion_records(user_id, limit=limit)

    def get_suggestion_record(self, user_id: str, suggestion_id: str) -> dict[str, Any] | None:
        return self._store.get_suggestion_record(user_id, suggestion_id)


@dataclass(slots=True)
class ProfileStore:
    _store: Any

    def get_health_profile(self, user_id: str) -> Any | None:
        return self._store.get_health_profile(user_id)

    def save_health_profile(self, profile: Any) -> Any:
        return self._store.save_health_profile(profile)

    def get_health_profile_onboarding_state(self, user_id: str) -> Any | None:
        return self._store.get_health_profile_onboarding_state(user_id)

    def save_health_profile_onboarding_state(self, state: Any) -> Any:
        return self._store.save_health_profile_onboarding_state(state)


@dataclass(slots=True)
class AlertStore:
    _store: Any

    def list_alert_records(self, alert_id: str | None = None) -> list[Any]:
        return self._store.list_alert_records(alert_id)


@dataclass(slots=True)
class AppStores:
    meals: MealStore
    biomarkers: BiomarkerStore
    symptoms: SymptomStore
    medications: MedicationStore
    reminders: ReminderStore
    clinical_cards: ClinicalCardStore
    workflows: WorkflowStore
    recommendations: RecommendationStore
    profiles: ProfileStore
    alerts: AlertStore


def build_app_stores(app_store: Any) -> AppStores:
    return AppStores(
        meals=MealStore(app_store),
        biomarkers=BiomarkerStore(app_store),
        symptoms=SymptomStore(app_store),
        medications=MedicationStore(app_store),
        reminders=ReminderStore(app_store),
        clinical_cards=ClinicalCardStore(app_store),
        workflows=WorkflowStore(app_store),
        recommendations=RecommendationStore(app_store),
        profiles=ProfileStore(app_store),
        alerts=AlertStore(app_store),
    )
