"""
Bootstrap SQLite persistence for local environments.

This module prepares the SQLite database and migrations for runtime use.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence

from care_pilot.features.recommendations.domain import (
    CanonicalFoodRecord,
    MealCatalogItem,
)
from care_pilot.features.recommendations.domain.canonical_food_matching import (
    build_default_canonical_food_records,
    normalize_text,
)
from care_pilot.features.recommendations.domain.meal_catalog_queries import (
    DEFAULT_MEAL_CATALOG,
)

SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
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
    """,
    """
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
    """,
    """
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
    """,
    """
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
    """,
    """
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
    """,
    """
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
    """,
    """
    CREATE TABLE IF NOT EXISTS meal_observations (
        observation_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        captured_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS meal_validated_events (
        event_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        captured_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS meal_nutrition_risk_profiles (
        profile_id TEXT PRIMARY KEY,
        event_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        captured_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
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
    """,
    """
    CREATE TABLE IF NOT EXISTS recommendation_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS suggestion_records (
        suggestion_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS health_profiles (
        user_id TEXT PRIMARY KEY,
        updated_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS health_profile_onboarding_states (
        user_id TEXT PRIMARY KEY,
        updated_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS meal_catalog (
        meal_id TEXT PRIMARY KEY,
        locale TEXT NOT NULL,
        slot TEXT NOT NULL,
        active INTEGER NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS canonical_foods (
        food_id TEXT PRIMARY KEY,
        locale TEXT NOT NULL,
        slot TEXT NOT NULL,
        active INTEGER NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS food_alias (
        alias TEXT NOT NULL,
        food_id TEXT NOT NULL,
        alias_type TEXT NOT NULL,
        priority INTEGER NOT NULL,
        PRIMARY KEY (alias, food_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS portion_reference (
        food_id TEXT NOT NULL,
        unit TEXT NOT NULL,
        grams REAL NOT NULL,
        confidence REAL NOT NULL,
        PRIMARY KEY (food_id, unit)
    )
    """,
    """
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
    """,
    """
    CREATE TABLE IF NOT EXISTS preference_snapshots (
        user_id TEXT PRIMARY KEY,
        updated_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS symptom_checkins (
        checkin_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        symptom_name TEXT NOT NULL,
        severity INTEGER NOT NULL,
        note TEXT,
        occurred_at TEXT NOT NULL,
        meal_id TEXT,
        safety_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS clinical_cards (
        card_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        title TEXT NOT NULL,
        summary TEXT NOT NULL,
        status TEXT NOT NULL,
        severity TEXT NOT NULL,
        created_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS medication_adherence_events (
        event_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        regimen_id TEXT NOT NULL,
        reminder_id TEXT,
        status TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        metadata_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reminder_notification_preferences (
        preference_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        scope_type TEXT NOT NULL,
        scope_key TEXT,
        channel TEXT NOT NULL,
        offset_minutes INTEGER NOT NULL,
        enabled INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS scheduled_notifications (
        notification_id TEXT PRIMARY KEY,
        reminder_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        channel TEXT NOT NULL,
        trigger_at TEXT NOT NULL,
        offset_minutes INTEGER NOT NULL,
        preference_id TEXT,
        status TEXT NOT NULL,
        attempt_count INTEGER NOT NULL,
        next_attempt_at TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        idempotency_key TEXT NOT NULL UNIQUE,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notification_logs (
        log_id TEXT PRIMARY KEY,
        scheduled_notification_id TEXT NOT NULL,
        reminder_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        channel TEXT NOT NULL,
        attempt_number INTEGER NOT NULL DEFAULT 0,
        event_type TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reminder_notification_endpoints (
        endpoint_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        channel TEXT NOT NULL,
        destination TEXT NOT NULL,
        verified INTEGER NOT NULL,
        label TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, channel, destination)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mobility_reminder_settings (
        user_id TEXT PRIMARY KEY,
        payload_json TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_role_policies (
        policy_id TEXT PRIMARY KEY,
        role TEXT NOT NULL,
        agent_id TEXT NOT NULL,
        tool_name TEXT NOT NULL,
        enabled INTEGER NOT NULL,
        constraints_json TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS workflow_timeline_events (
        event_id TEXT PRIMARY KEY,
        event_type TEXT NOT NULL,
        workflow_name TEXT,
        correlation_id TEXT NOT NULL,
        request_id TEXT,
        user_id TEXT,
        created_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS alert_outbox (
        outbox_id TEXT PRIMARY KEY,
        alert_id TEXT NOT NULL,
        sink TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        state TEXT NOT NULL,
        attempt_count INTEGER NOT NULL,
        max_attempts INTEGER NOT NULL,
        destination TEXT,
        provider_reference TEXT,
        next_attempt_at TEXT NOT NULL,
        delivered_at TEXT,
        dead_lettered_at TEXT,
        last_error TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(alert_id, sink)
    )
    """,
)

COLUMN_MIGRATIONS: tuple[tuple[str, str, str], ...] = (
    ("meal_records", "meal_perception_json", "TEXT"),
    ("meal_records", "enriched_event_json", "TEXT"),
    ("meal_records", "multi_item_count", "INTEGER NOT NULL DEFAULT 1"),
    ("medication_regimens", "canonical_name", "TEXT"),
    (
        "medication_regimens",
        "frequency_type",
        "TEXT NOT NULL DEFAULT 'fixed_time'",
    ),
    (
        "medication_regimens",
        "frequency_times_per_day",
        "INTEGER NOT NULL DEFAULT 1",
    ),
    ("medication_regimens", "time_rules_json", "TEXT NOT NULL DEFAULT '[]'"),
    ("medication_regimens", "instructions_text", "TEXT"),
    ("medication_regimens", "source_type", "TEXT NOT NULL DEFAULT 'manual'"),
    ("medication_regimens", "source_filename", "TEXT"),
    ("medication_regimens", "source_hash", "TEXT"),
    ("medication_regimens", "start_date", "TEXT"),
    ("medication_regimens", "end_date", "TEXT"),
    (
        "medication_regimens",
        "timezone",
        "TEXT NOT NULL DEFAULT 'Asia/Singapore'",
    ),
    ("medication_regimens", "parse_confidence", "REAL"),
    ("reminder_events", "reminder_type", "TEXT NOT NULL DEFAULT 'medication'"),
    ("reminder_events", "reminder_definition_id", "TEXT"),
    ("reminder_events", "occurrence_id", "TEXT"),
    ("reminder_events", "regimen_id", "TEXT"),
    (
        "reminder_events",
        "title",
        "TEXT NOT NULL DEFAULT 'Medication Reminder'",
    ),
    ("reminder_events", "body", "TEXT"),
    ("scheduled_notifications", "occurrence_id", "TEXT"),
    ("notification_logs", "occurrence_id", "TEXT"),
)


def ensure_sqlite_column(
    cur: sqlite3.Cursor, table: str, column: str, definition: str
) -> None:
    cur.execute(f"PRAGMA table_info({table})")
    columns = {row[1] for row in cur.fetchall()}
    if column not in columns:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def bootstrap_sqlite_store(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        for statement in SCHEMA_STATEMENTS:
            cur.execute(statement)
        for table, column, definition in COLUMN_MIGRATIONS:
            ensure_sqlite_column(cur, table, column, definition)
        conn.commit()
    seed_reference_data(db_path)


def seed_reference_data(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        _seed_meal_catalog(cur, DEFAULT_MEAL_CATALOG)
        _seed_canonical_foods(cur, build_default_canonical_food_records())
        conn.commit()


def _seed_meal_catalog(
    cur: sqlite3.Cursor, items: Sequence[MealCatalogItem]
) -> None:
    cur.execute("SELECT COUNT(*) FROM meal_catalog")
    existing = cur.fetchone()
    if existing is not None and int(existing[0]) > 0:
        return
    for item in items:
        cur.execute(
            """
            INSERT OR IGNORE INTO meal_catalog (meal_id, locale, slot, active, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                item.meal_id,
                item.locale,
                item.slot,
                int(item.active),
                item.model_dump_json(),
            ),
        )


def _seed_canonical_foods(
    cur: sqlite3.Cursor, records: Sequence[CanonicalFoodRecord]
) -> None:
    cur.execute("SELECT COUNT(*) FROM canonical_foods")
    existing = cur.fetchone()
    if existing is None or int(existing[0]) == 0:
        for item in records:
            cur.execute(
                """
                INSERT OR IGNORE INTO canonical_foods (food_id, locale, slot, active, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    item.food_id,
                    item.locale,
                    item.slot,
                    int(item.active),
                    item.model_dump_json(),
                ),
            )
    cur.execute("SELECT COUNT(*) FROM food_alias")
    alias_existing = cur.fetchone()
    if alias_existing is None or int(alias_existing[0]) == 0:
        for item in records:
            for index, alias in enumerate(
                item.aliases_normalized or [normalize_text(item.title)],
                start=1,
            ):
                cur.execute(
                    """
                    INSERT OR IGNORE INTO food_alias (alias, food_id, alias_type, priority)
                    VALUES (?, ?, ?, ?)
                    """,
                    (alias, item.food_id, "canonical", index),
                )
    cur.execute("SELECT COUNT(*) FROM portion_reference")
    portion_existing = cur.fetchone()
    if portion_existing is None or int(portion_existing[0]) == 0:
        for item in records:
            for portion in item.portion_references:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO portion_reference (food_id, unit, grams, confidence)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        item.food_id,
                        portion.unit,
                        portion.grams,
                        portion.confidence,
                    ),
                )
