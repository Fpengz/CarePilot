"""
Provide SQLite repository base helpers.

This module contains shared helpers used by SQLite-backed repositories.
"""

import json
from pathlib import Path
from typing import Any, cast

from care_pilot.core.contracts.notifications import ReminderSchedulerRepository
from care_pilot.features.recommendations.domain.canonical_food_matching import (
    build_default_canonical_food_records,
    normalize_text,
)
from care_pilot.features.recommendations.domain.meal_catalog_queries import DEFAULT_MEAL_CATALOG
from care_pilot.platform.observability import get_logger
from care_pilot.platform.persistence.sqlite_db import get_connection

from .schema import INDEX_STATEMENTS, SCHEMA_STATEMENTS, migrate_schema
from .sqlite_alert_repository import SQLiteAlertRepository
from .sqlite_catalog_repository import SQLiteCatalogRepository
from .sqlite_clinical_repository import SQLiteClinicalRepository
from .sqlite_eventing_repository import SQLiteEventingRepository
from .sqlite_meal_repository import SQLiteMealRepository
from .sqlite_medication_repository import SQLiteMedicationRepository
from .sqlite_reminder_repository import SQLiteReminderRepository
from .sqlite_workflow_repository import SQLiteWorkflowRepository

logger = get_logger(__name__)


class SQLiteRepository(ReminderSchedulerRepository):
    """
    Composite SQLite repository aggregating all domain-specific stores.

    SQLiteRepository acts as the primary persistence backend for local-first
    deployments. It composes specialized sub-repositories for medications,
    reminders, meals, and other domain entities while providing a unified
    interface for application stores.
    """
    def __init__(self, db_path: str = "data/care_pilot_api.db", *, skip_init: bool = False):
        self.db_path = db_path
        logger.info("repository_init db_path=%s", db_path)
        self.medication = SQLiteMedicationRepository(db_path)
        self.reminders = SQLiteReminderRepository(db_path)
        self.meals = SQLiteMealRepository(db_path)
        self.clinical = SQLiteClinicalRepository(db_path)
        self.catalog = SQLiteCatalogRepository(db_path)
        self.alerts = SQLiteAlertRepository(db_path)
        self.workflows = SQLiteWorkflowRepository(db_path)
        self.eventing = SQLiteEventingRepository(db_path)

        # Initialize schema if not skipped
        if not skip_init:
            self._init_db()

    def _init_db(self) -> None:
        # Ensure correct file permissions for the DB file
        db_path_obj = Path(self.db_path)
        if not db_path_obj.exists():
            db_path_obj.parent.mkdir(parents=True, exist_ok=True)
            # Create empty file with restricted permissions
            with open(db_path_obj, "w"):
                pass
            db_path_obj.chmod(0o600)

        with get_connection(self.db_path) as conn:
            cur = conn.cursor()
            for statement in SCHEMA_STATEMENTS:
                cur.execute(statement)
            for statement in INDEX_STATEMENTS:
                cur.execute(statement)

            migrate_schema(cur)
            conn.commit()

        self._seed_meal_catalog()
        self._seed_canonical_foods()
        logger.info("repository_schema_ready db_path=%s", self.db_path)

    def _seed_meal_catalog(self) -> None:
        with get_connection(self.db_path) as conn:
            existing = conn.execute("SELECT COUNT(*) FROM meal_catalog").fetchone()
            if existing is not None and int(existing[0]) > 0:
                return
            for item in DEFAULT_MEAL_CATALOG:
                payload = item.model_dump(mode="json")
                conn.execute(
                    """
                    INSERT INTO meal_catalog (meal_id, locale, slot, active, payload_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        item.meal_id,
                        item.locale,
                        item.slot,
                        int(item.active),
                        json.dumps(payload),
                    ),
                )
            conn.commit()

    def _seed_canonical_foods(self) -> None:
        with get_connection(self.db_path) as conn:
            records = build_default_canonical_food_records()
            existing = conn.execute("SELECT COUNT(*) FROM canonical_foods").fetchone()
            if not existing or int(cast(int, existing[0])) == 0:
                conn.executemany(
                    """
                    INSERT INTO canonical_foods (food_id, locale, slot, active, payload_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            item.food_id,
                            item.locale,
                            item.slot,
                            1 if item.active else 0,
                            item.model_dump_json(),
                        )
                        for item in records
                    ],
                )
            alias_existing = conn.execute("SELECT COUNT(*) FROM food_alias").fetchone()
            if not alias_existing or int(cast(int, alias_existing[0])) == 0:
                conn.executemany(
                    """
                    INSERT INTO food_alias (alias, food_id, alias_type, priority)
                    VALUES (?, ?, ?, ?)
                    """,
                    [
                        (alias, item.food_id, "canonical", index)
                        for item in records
                        for index, alias in enumerate(
                            item.aliases_normalized or [normalize_text(item.title)],
                            start=1,
                        )
                    ],
                )
            portion_existing = conn.execute("SELECT COUNT(*) FROM portion_reference").fetchone()
            if not portion_existing or int(cast(int, portion_existing[0])) == 0:
                conn.executemany(
                    """
                    INSERT INTO portion_reference (food_id, unit, grams, confidence)
                    VALUES (?, ?, ?, ?)
                    """,
                    [
                        (
                            item.food_id,
                            portion.unit,
                            portion.grams,
                            portion.confidence,
                        )
                        for item in records
                        for portion in item.portion_references
                    ],
                )
            conn.commit()

    def close(self) -> None:
        return None

    # --- Medication ---

    def save_medication_regimen(self, *args: Any, **kwargs: Any) -> Any:
        return self.medication.save_medication_regimen(*args, **kwargs)

    def list_medication_regimens(self, *args: Any, **kwargs: Any) -> Any:
        return self.medication.list_medication_regimens(*args, **kwargs)

    def get_medication_regimen(self, *args: Any, **kwargs: Any) -> Any:
        return self.medication.get_medication_regimen(*args, **kwargs)

    def delete_medication_regimen(self, *args: Any, **kwargs: Any) -> Any:
        return self.medication.delete_medication_regimen(*args, **kwargs)

    def save_medication_adherence_event(self, *args: Any, **kwargs: Any) -> Any:
        return self.medication.save_medication_adherence_event(*args, **kwargs)

    def list_medication_adherence_events(self, *args: Any, **kwargs: Any) -> Any:
        return self.medication.list_medication_adherence_events(*args, **kwargs)

    # --- Reminders ---

    def save_reminder_definition(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.save_reminder_definition(*args, **kwargs)

    def get_reminder_definition(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.get_reminder_definition(*args, **kwargs)

    def list_reminder_definitions(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.list_reminder_definitions(*args, **kwargs)

    def save_reminder_occurrence(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.save_reminder_occurrence(*args, **kwargs)

    def get_reminder_occurrence(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.get_reminder_occurrence(*args, **kwargs)

    def list_reminder_occurrences(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.list_reminder_occurrences(*args, **kwargs)

    def append_reminder_action(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.append_reminder_action(*args, **kwargs)

    def list_reminder_actions(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.list_reminder_actions(*args, **kwargs)

    def update_reminder_occurrence_status(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.update_reminder_occurrence_status(*args, **kwargs)

    def save_reminder_event(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.save_reminder_event(*args, **kwargs)

    def get_reminder_event(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.get_reminder_event(*args, **kwargs)

    def list_reminder_events(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.list_reminder_events(*args, **kwargs)

    def list_message_preferences(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.list_message_preferences(*args, **kwargs)

    def replace_message_preferences(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.replace_message_preferences(*args, **kwargs)

    def list_message_endpoints(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.list_message_endpoints(*args, **kwargs)

    def replace_message_endpoints(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.replace_message_endpoints(*args, **kwargs)

    def list_message_logs(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.list_message_logs(*args, **kwargs)

    def list_message_schedules(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.list_scheduled_messages(*args, **kwargs)

    def list_scheduled_messages(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.list_scheduled_messages(*args, **kwargs)

    def lease_due_scheduled_messages(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.lease_due_scheduled_messages(*args, **kwargs)

    def cancel_scheduled_messages_for_reminder(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.cancel_scheduled_messages_for_reminder(*args, **kwargs)

    def get_message_thread(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.get_message_thread(*args, **kwargs)

    def create_message_thread(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.create_message_thread(*args, **kwargs)

    def add_message_thread_participant(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.add_message_thread_participant(*args, **kwargs)

    def append_message_thread_message(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.append_message_thread_message(*args, **kwargs)

    def list_message_thread_messages(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.list_message_thread_messages(*args, **kwargs)

    def get_message_endpoint(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.get_message_endpoint(*args, **kwargs)

    def get_message_endpoint_by_destination(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.get_message_endpoint_by_destination(*args, **kwargs)

    # --- Legacy Aliases (optional but keeping for compat) ---

    def replace_reminder_notification_preferences(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.replace_reminder_notification_preferences(*args, **kwargs)

    def list_reminder_notification_preferences(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.list_reminder_notification_preferences(*args, **kwargs)

    def save_scheduled_notification(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.save_scheduled_notification(*args, **kwargs)

    def get_scheduled_notification(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.get_scheduled_notification(*args, **kwargs)

    def list_scheduled_notifications(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.list_scheduled_notifications(*args, **kwargs)

    def lease_due_scheduled_notifications(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.lease_due_scheduled_notifications(*args, **kwargs)

    def set_scheduled_notification_trigger_at(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.set_scheduled_notification_trigger_at(*args, **kwargs)

    def mark_scheduled_notification_processing(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.mark_scheduled_notification_processing(*args, **kwargs)

    def mark_scheduled_notification_delivered(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.mark_scheduled_notification_delivered(*args, **kwargs)

    def reschedule_scheduled_notification(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.reschedule_scheduled_notification(*args, **kwargs)

    def mark_scheduled_notification_dead_letter(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.mark_scheduled_notification_dead_letter(*args, **kwargs)

    def cancel_scheduled_notifications_for_reminder(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.cancel_scheduled_messages_for_reminder(*args, **kwargs)

    def append_notification_log(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.append_notification_log(*args, **kwargs)

    def replace_reminder_notification_endpoints(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.replace_reminder_notification_endpoints(*args, **kwargs)

    def list_reminder_notification_endpoints(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.list_reminder_notification_endpoints(*args, **kwargs)

    def get_reminder_notification_endpoint(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.get_reminder_notification_endpoint(*args, **kwargs)

    def list_notification_logs(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.list_notification_logs(*args, **kwargs)

    def get_mobility_reminder_settings(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.get_mobility_reminder_settings(*args, **kwargs)

    def save_mobility_reminder_settings(self, *args: Any, **kwargs: Any) -> Any:
        return self.reminders.save_mobility_reminder_settings(*args, **kwargs)

    # --- Meals ---

    def save_meal_record(self, *args: Any, **kwargs: Any) -> Any:
        return self.meals.save_meal_record(*args, **kwargs)

    def list_meal_records(self, *args: Any, **kwargs: Any) -> Any:
        return self.meals.list_meal_records(*args, **kwargs)

    def get_meal_record(self, *args: Any, **kwargs: Any) -> Any:
        return self.meals.get_meal_record(*args, **kwargs)

    def save_meal_observation(self, *args: Any, **kwargs: Any) -> Any:
        return self.meals.save_meal_observation(*args, **kwargs)

    def list_meal_observations(self, *args: Any, **kwargs: Any) -> Any:
        return self.meals.list_meal_observations(*args, **kwargs)

    def save_meal_candidate(self, *args: Any, **kwargs: Any) -> Any:
        return self.meals.save_meal_candidate(*args, **kwargs)

    def get_meal_candidate(self, *args: Any, **kwargs: Any) -> Any:
        return self.meals.get_meal_candidate(*args, **kwargs)

    def save_validated_meal_event(self, *args: Any, **kwargs: Any) -> Any:
        return self.meals.save_validated_meal_event(*args, **kwargs)

    def list_validated_meal_events(self, *args: Any, **kwargs: Any) -> Any:
        return self.meals.list_validated_meal_events(*args, **kwargs)

    def get_validated_meal_event(self, *args: Any, **kwargs: Any) -> Any:
        return self.meals.get_validated_meal_event(*args, **kwargs)

    def save_nutrition_risk_profile(self, *args: Any, **kwargs: Any) -> Any:
        return self.meals.save_nutrition_risk_profile(*args, **kwargs)

    def list_nutrition_risk_profiles(self, *args: Any, **kwargs: Any) -> Any:
        return self.meals.list_nutrition_risk_profiles(*args, **kwargs)

    def get_nutrition_risk_profile(self, *args: Any, **kwargs: Any) -> Any:
        return self.meals.get_nutrition_risk_profile(*args, **kwargs)

    # --- Clinical ---

    def save_biomarker_readings(self, *args: Any, **kwargs: Any) -> Any:
        return self.clinical.save_biomarker_readings(*args, **kwargs)

    def save_biomarker_reading(self, *args: Any, **kwargs: Any) -> Any:
        return self.clinical.save_biomarker_reading(*args, **kwargs)

    def list_biomarker_readings(self, *args: Any, **kwargs: Any) -> Any:
        return self.clinical.list_biomarker_readings(*args, **kwargs)

    def save_symptom_checkin(self, *args: Any, **kwargs: Any) -> Any:
        return self.clinical.save_symptom_checkin(*args, **kwargs)

    def save_health_profile(self, *args: Any, **kwargs: Any) -> Any:
        return self.clinical.save_health_profile(*args, **kwargs)

    def get_health_profile(self, *args: Any, **kwargs: Any) -> Any:
        return self.clinical.get_health_profile(*args, **kwargs)

    def list_symptom_checkins(self, *args: Any, **kwargs: Any) -> Any:
        return self.clinical.list_symptom_checkins(*args, **kwargs)

    def save_clinical_card(self, *args: Any, **kwargs: Any) -> Any:
        return self.clinical.save_clinical_card(*args, **kwargs)

    def list_clinical_cards(self, *args: Any, **kwargs: Any) -> Any:
        return self.clinical.list_clinical_cards(*args, **kwargs)

    def get_clinical_card(self, *args: Any, **kwargs: Any) -> Any:
        return self.clinical.get_clinical_card(*args, **kwargs)

    def get_health_profile_onboarding_state(self, *args: Any, **kwargs: Any) -> Any:
        return self.clinical.get_health_profile_onboarding_state(*args, **kwargs)

    def save_health_profile_onboarding_state(self, *args: Any, **kwargs: Any) -> Any:
        return self.clinical.save_health_profile_onboarding_state(*args, **kwargs)

    def get_health_profile_for_user(self, *args: Any, **kwargs: Any) -> Any:
        return self.clinical.get_health_profile(*args, **kwargs)

    # --- Catalog ---

    def save_recommendation(self, *args: Any, **kwargs: Any) -> Any:
        return self.catalog.save_recommendation(*args, **kwargs)

    def list_meal_catalog_items(self, *args: Any, **kwargs: Any) -> Any:
        return self.catalog.list_meal_catalog_items(*args, **kwargs)

    def get_meal_catalog_item(self, *args: Any, **kwargs: Any) -> Any:
        return self.catalog.get_meal_catalog_item(*args, **kwargs)

    def list_canonical_foods(self, *args: Any, **kwargs: Any) -> Any:
        return self.catalog.list_canonical_foods(*args, **kwargs)

    def get_canonical_food(self, *args: Any, **kwargs: Any) -> Any:
        return self.catalog.get_canonical_food(*args, **kwargs)

    def find_food_by_name(self, *args: Any, **kwargs: Any) -> Any:
        return self.catalog.find_food_by_name(*args, **kwargs)

    def save_recommendation_interaction(self, *args: Any, **kwargs: Any) -> Any:
        return self.catalog.save_recommendation_interaction(*args, **kwargs)

    def list_recommendation_interactions(self, *args: Any, **kwargs: Any) -> Any:
        return self.catalog.list_recommendation_interactions(*args, **kwargs)

    def get_preference_snapshot(self, *args: Any, **kwargs: Any) -> Any:
        return self.catalog.get_preference_snapshot(*args, **kwargs)

    def save_preference_snapshot(self, *args: Any, **kwargs: Any) -> Any:
        return self.catalog.save_preference_snapshot(*args, **kwargs)

    def save_suggestion_record(self, *args: Any, **kwargs: Any) -> Any:
        return self.catalog.save_suggestion_record(*args, **kwargs)

    def list_suggestion_records(self, *args: Any, **kwargs: Any) -> Any:
        return self.catalog.list_suggestion_records(*args, **kwargs)

    def get_suggestion_record(self, *args: Any, **kwargs: Any) -> Any:
        return self.catalog.get_suggestion_record(*args, **kwargs)

    # --- Alerts ---

    def enqueue_alert(self, *args: Any, **kwargs: Any) -> Any:
        return self.alerts.enqueue_alert(*args, **kwargs)

    def lease_alert_records(self, *args: Any, **kwargs: Any) -> Any:
        return self.alerts.lease_alert_records(*args, **kwargs)

    def mark_alert_delivered(self, *args: Any, **kwargs: Any) -> Any:
        return self.alerts.mark_alert_delivered(*args, **kwargs)

    def reschedule_alert(self, *args: Any, **kwargs: Any) -> Any:
        return self.alerts.reschedule_alert(*args, **kwargs)

    def mark_alert_dead_letter(self, *args: Any, **kwargs: Any) -> Any:
        return self.alerts.mark_alert_dead_letter(*args, **kwargs)

    def list_alert_records(self, *args: Any, **kwargs: Any) -> Any:
        return self.alerts.list_alert_records(*args, **kwargs)

    # --- Workflows ---

    def save_tool_role_policy(self, *args: Any, **kwargs: Any) -> Any:
        return self.workflows.save_tool_role_policy(*args, **kwargs)

    def list_tool_role_policies(self, *args: Any, **kwargs: Any) -> Any:
        return self.workflows.list_tool_role_policies(*args, **kwargs)

    def get_tool_role_policy(self, *args: Any, **kwargs: Any) -> Any:
        return self.workflows.get_tool_role_policy(*args, **kwargs)

    def save_workflow_timeline_event(self, *args: Any, **kwargs: Any) -> Any:
        return self.workflows.save_workflow_timeline_event(*args, **kwargs)

    def list_workflow_timeline_events(self, *args: Any, **kwargs: Any) -> Any:
        return self.workflows.list_workflow_timeline_events(*args, **kwargs)

    def save_reaction_execution(self, *args: Any, **kwargs: Any) -> Any:
        return self.eventing.save_reaction_execution(*args, **kwargs)

    def get_reaction_execution(self, *args: Any, **kwargs: Any) -> Any:
        return self.eventing.get_reaction_execution(*args, **kwargs)

    def upsert_snapshot_section(self, *args: Any, **kwargs: Any) -> Any:
        return self.eventing.upsert_snapshot_section(*args, **kwargs)

    def get_snapshot_section(self, *args: Any, **kwargs: Any) -> Any:
        return self.eventing.get_snapshot_section(*args, **kwargs)

    def list_snapshot_sections(self, *args: Any, **kwargs: Any) -> Any:
        return self.eventing.list_snapshot_sections(*args, **kwargs)

    def upsert_event_handler_cursor(self, *args: Any, **kwargs: Any) -> Any:
        return self.eventing.upsert_event_handler_cursor(*args, **kwargs)

    def get_event_handler_cursor(self, *args: Any, **kwargs: Any) -> Any:
        return self.eventing.get_event_handler_cursor(*args, **kwargs)

    def list_event_handler_cursors(self, *args: Any, **kwargs: Any) -> Any:
        return self.eventing.list_event_handler_cursors(*args, **kwargs)

    def prune_events(self, *args: Any, **kwargs: Any) -> Any:
        return self.workflows.prune_events(*args, **kwargs)
