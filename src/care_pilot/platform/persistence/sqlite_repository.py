"""
Provide SQLite repository base helpers.

This module contains shared helpers used by SQLite-backed repositories.
"""

import json
import sqlite3
from typing import Any, cast

from care_pilot.features.recommendations.domain.canonical_food_matching import (
    build_default_canonical_food_records,
    normalize_text,
)
from care_pilot.features.recommendations.domain.meal_catalog_queries import (
    DEFAULT_MEAL_CATALOG,
)
from care_pilot.platform.observability.setup import get_logger

from .sqlite_alert_repository import SQLiteAlertRepository
from .sqlite_catalog_repository import SQLiteCatalogRepository
from .sqlite_clinical_repository import SQLiteClinicalRepository
from .sqlite_meal_repository import SQLiteMealRepository
from .sqlite_medication_repository import SQLiteMedicationRepository
from .sqlite_reminder_repository import SQLiteReminderRepository
from .sqlite_workflow_repository import SQLiteWorkflowRepository

logger = get_logger(__name__)


class SQLiteRepository:
    def __init__(self, db_path: str = "care_pilot.db"):
        self.db_path = db_path
        logger.info("repository_init db_path=%s", db_path)
        self._init_db()
        self.medication = SQLiteMedicationRepository(db_path)
        self.reminders = SQLiteReminderRepository(db_path)
        self.meals = SQLiteMealRepository(db_path)
        self.clinical = SQLiteClinicalRepository(db_path)
        self.catalog = SQLiteCatalogRepository(db_path)
        self.alerts = SQLiteAlertRepository(db_path)
        self.workflows = SQLiteWorkflowRepository(db_path)

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS medication_regimens (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    medication_name TEXT NOT NULL,
                    canonical_name TEXT,
                    dosage_text TEXT NOT NULL,
                    timing_type TEXT NOT NULL,
                    frequency_type TEXT NOT NULL DEFAULT 'fixed_time',
                    frequency_times_per_day INTEGER NOT NULL DEFAULT 1,
                    time_rules_json TEXT NOT NULL DEFAULT '[]',
                    offset_minutes INTEGER NOT NULL,
                    slot_scope_json TEXT NOT NULL,
                    fixed_time TEXT,
                    max_daily_doses INTEGER NOT NULL,
                    instructions_text TEXT,
                    source_type TEXT NOT NULL DEFAULT 'manual',
                    source_filename TEXT,
                    source_hash TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    timezone TEXT NOT NULL DEFAULT 'Asia/Singapore',
                    parse_confidence REAL,
                    active INTEGER NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reminder_events (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    reminder_definition_id TEXT,
                    occurrence_id TEXT,
                    regimen_id TEXT,
                    reminder_type TEXT NOT NULL DEFAULT 'medication',
                    title TEXT NOT NULL DEFAULT 'Medication Reminder',
                    body TEXT,
                    medication_name TEXT NOT NULL,
                    scheduled_at TEXT NOT NULL,
                    slot TEXT,
                    dosage_text TEXT NOT NULL,
                    status TEXT NOT NULL,
                    meal_confirmation TEXT NOT NULL,
                    sent_at TEXT,
                    ack_at TEXT
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reminder_definitions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    regimen_id TEXT,
                    reminder_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT,
                    medication_name TEXT NOT NULL,
                    dosage_text TEXT NOT NULL,
                    route TEXT,
                    instructions_text TEXT,
                    special_notes TEXT,
                    treatment_duration TEXT,
                    channels_json TEXT NOT NULL,
                    timezone TEXT NOT NULL,
                    schedule_json TEXT NOT NULL,
                    active INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reminder_occurrences (
                    id TEXT PRIMARY KEY,
                    reminder_definition_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    scheduled_for TEXT NOT NULL,
                    trigger_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    action TEXT,
                    action_outcome TEXT,
                    acted_at TEXT,
                    grace_window_minutes INTEGER NOT NULL,
                    retry_count INTEGER NOT NULL,
                    last_delivery_status TEXT,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reminder_actions (
                    id TEXT PRIMARY KEY,
                    occurrence_id TEXT NOT NULL,
                    reminder_definition_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    acted_at TEXT NOT NULL,
                    snooze_minutes INTEGER,
                    metadata_json TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS meal_records (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    meal_state_json TEXT NOT NULL,
                    meal_perception_json TEXT,
                    enriched_event_json TEXT,
                    analysis_version TEXT NOT NULL,
                    multi_item_count INTEGER NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS meal_observations (
                    observation_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS meal_validated_events (
                    event_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS meal_candidates (
                    candidate_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    confirmation_status TEXT NOT NULL,
                    candidate_event_json TEXT NOT NULL,
                    observation_id TEXT,
                    request_id TEXT,
                    correlation_id TEXT,
                    source TEXT,
                    meal_text TEXT,
                    confirmed_at TEXT,
                    skipped_at TEXT,
                    validated_event_json TEXT,
                    nutrition_profile_json TEXT
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS meal_nutrition_risk_profiles (
                    profile_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS biomarker_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT,
                    reference_range TEXT,
                    measured_at TEXT,
                    source_doc_id TEXT
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS recommendation_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS suggestion_records (
                    suggestion_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS health_profiles (
                    user_id TEXT PRIMARY KEY,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS health_profile_onboarding_states (
                    user_id TEXT PRIMARY KEY,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS meal_catalog (
                    meal_id TEXT PRIMARY KEY,
                    locale TEXT NOT NULL,
                    slot TEXT NOT NULL,
                    active INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS canonical_foods (
                    food_id TEXT PRIMARY KEY,
                    locale TEXT NOT NULL,
                    slot TEXT NOT NULL,
                    active INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS food_alias (
                    alias TEXT NOT NULL,
                    food_id TEXT NOT NULL,
                    alias_type TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    PRIMARY KEY (alias, food_id)
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS portion_reference (
                    food_id TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    grams REAL NOT NULL,
                    confidence REAL NOT NULL,
                    PRIMARY KEY (food_id, unit)
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS recommendation_interactions (
                    interaction_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    recommendation_id TEXT NOT NULL,
                    candidate_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    slot TEXT NOT NULL,
                    source_meal_id TEXT,
                    selected_meal_id TEXT,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS preference_snapshots (
                    user_id TEXT PRIMARY KEY,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS alert_outbox (
                    alert_id TEXT NOT NULL,
                    sink TEXT NOT NULL,
                    type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    next_attempt_at TEXT NOT NULL,
                    last_error TEXT,
                    lease_owner TEXT,
                    lease_until TEXT,
                    idempotency_key TEXT NOT NULL,
                    PRIMARY KEY (alert_id, sink)
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reminder_notification_preferences (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    scope_type TEXT NOT NULL,
                    scope_key TEXT,
                    channel TEXT NOT NULL,
                    offset_minutes INTEGER NOT NULL,
                    enabled INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, scope_type, scope_key, channel, offset_minutes)
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_notifications (
                    id TEXT PRIMARY KEY,
                    reminder_id TEXT NOT NULL,
                    occurrence_id TEXT,
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    trigger_at TEXT NOT NULL,
                    offset_minutes INTEGER NOT NULL,
                    preference_id TEXT,
                    status TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    next_attempt_at TEXT,
                    queued_at TEXT,
                    delivered_at TEXT,
                    last_error TEXT,
                    payload_json TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS notification_logs (
                    id TEXT PRIMARY KEY,
                    scheduled_notification_id TEXT NOT NULL,
                    reminder_id TEXT NOT NULL,
                    occurrence_id TEXT,
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    attempt_number INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    error_message TEXT,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reminder_notification_endpoints (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    verified INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, channel)
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS mobility_reminder_settings (
                    user_id TEXT PRIMARY KEY,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS medication_adherence_events (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    regimen_id TEXT NOT NULL,
                    reminder_id TEXT,
                    status TEXT NOT NULL,
                    scheduled_at TEXT NOT NULL,
                    taken_at TEXT,
                    source TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS symptom_checkins (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    severity INTEGER NOT NULL,
                    symptom_codes_json TEXT NOT NULL,
                    free_text TEXT,
                    context_json TEXT NOT NULL,
                    safety_json TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS clinical_cards (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    format TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tool_role_policies (
                    id TEXT PRIMARY KEY,
                    role TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    effect TEXT NOT NULL,
                    conditions_json TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    enabled INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS workflow_timeline_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    workflow_name TEXT,
                    request_id TEXT,
                    correlation_id TEXT NOT NULL,
                    user_id TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """)
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_reminders_user_time ON reminder_events(user_id, scheduled_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_reminder_definitions_user_active ON reminder_definitions(user_id, active, updated_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_reminder_occurrences_user_status_time ON reminder_occurrences(user_id, status, trigger_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_reminder_actions_occurrence_time ON reminder_actions(occurrence_id, acted_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_meals_user_time ON meal_records(user_id, captured_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_meal_observations_user_time ON meal_observations(user_id, captured_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_meal_events_user_time ON meal_validated_events(user_id, captured_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_meal_candidates_user_time ON meal_candidates(user_id, captured_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_meal_nutrition_user_time ON meal_nutrition_risk_profiles(user_id, captured_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_biomarkers_user_time_name ON biomarker_readings(user_id, measured_at, name)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_suggestions_user_time ON suggestion_records(user_id, created_at DESC)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_health_profiles_updated_at ON health_profiles(updated_at DESC)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_health_profile_onboarding_updated_at ON health_profile_onboarding_states(updated_at DESC)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_meal_catalog_locale_slot ON meal_catalog(locale, slot)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_canonical_foods_locale_slot ON canonical_foods(locale, slot)"
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_food_alias_lookup ON food_alias(alias)")
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_portion_reference_food ON portion_reference(food_id)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_recommendation_interactions_user_time ON recommendation_interactions(user_id, created_at DESC)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_preference_snapshots_updated_at ON preference_snapshots(updated_at DESC)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_alert_outbox_next_attempt ON alert_outbox(state, next_attempt_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_reminder_notification_preferences_user_scope ON reminder_notification_preferences(user_id, scope_type, scope_key)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_scheduled_notifications_due ON scheduled_notifications(status, trigger_at, next_attempt_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_scheduled_notifications_reminder_id ON scheduled_notifications(reminder_id)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_notification_logs_reminder_created ON notification_logs(reminder_id, created_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_reminder_notification_endpoints_user_channel ON reminder_notification_endpoints(user_id, channel)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_adherence_user_time ON medication_adherence_events(user_id, scheduled_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_symptom_checkins_user_time ON symptom_checkins(user_id, recorded_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_clinical_cards_user_created ON clinical_cards(user_id, created_at DESC)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_tool_role_policies_lookup ON tool_role_policies(role, agent_id, tool_name, enabled, priority DESC)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_workflow_timeline_corr_created ON workflow_timeline_events(correlation_id, created_at)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_workflow_timeline_user_created ON workflow_timeline_events(user_id, created_at)"
            )
            self._ensure_sqlite_column(cur, "meal_records", "meal_perception_json", "TEXT")
            self._ensure_sqlite_column(cur, "meal_records", "enriched_event_json", "TEXT")
            self._ensure_sqlite_column(cur, "medication_regimens", "canonical_name", "TEXT")
            self._ensure_sqlite_column(
                cur,
                "medication_regimens",
                "frequency_type",
                "TEXT NOT NULL DEFAULT 'fixed_time'",
            )
            self._ensure_sqlite_column(
                cur,
                "medication_regimens",
                "frequency_times_per_day",
                "INTEGER NOT NULL DEFAULT 1",
            )
            self._ensure_sqlite_column(
                cur,
                "medication_regimens",
                "time_rules_json",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_sqlite_column(cur, "medication_regimens", "instructions_text", "TEXT")
            self._ensure_sqlite_column(
                cur,
                "medication_regimens",
                "source_type",
                "TEXT NOT NULL DEFAULT 'manual'",
            )
            self._ensure_sqlite_column(cur, "medication_regimens", "source_filename", "TEXT")
            self._ensure_sqlite_column(cur, "medication_regimens", "source_hash", "TEXT")
            self._ensure_sqlite_column(cur, "medication_regimens", "start_date", "TEXT")
            self._ensure_sqlite_column(cur, "medication_regimens", "end_date", "TEXT")
            self._ensure_sqlite_column(
                cur,
                "medication_regimens",
                "timezone",
                "TEXT NOT NULL DEFAULT 'Asia/Singapore'",
            )
            self._ensure_sqlite_column(cur, "medication_regimens", "parse_confidence", "REAL")
            self._ensure_sqlite_column(cur, "reminder_events", "reminder_definition_id", "TEXT")
            self._ensure_sqlite_column(cur, "reminder_events", "occurrence_id", "TEXT")
            self._ensure_sqlite_column(cur, "reminder_events", "regimen_id", "TEXT")
            self._ensure_sqlite_column(cur, "scheduled_notifications", "occurrence_id", "TEXT")
            self._ensure_sqlite_column(cur, "notification_logs", "occurrence_id", "TEXT")
            conn.commit()
        self._seed_meal_catalog()
        self._seed_canonical_foods()
        logger.info("repository_schema_ready db_path=%s", self.db_path)

    @staticmethod
    def _ensure_sqlite_column(
        cur: sqlite3.Cursor, table: str, column: str, definition: str
    ) -> None:
        rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {str(row[1]) for row in rows}
        if column not in existing:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _seed_meal_catalog(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
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
        return self.reminders.cancel_scheduled_notifications_for_reminder(*args, **kwargs)

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

    def get_health_profile(self, *args: Any, **kwargs: Any) -> Any:
        return self.clinical.get_health_profile(*args, **kwargs)

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
