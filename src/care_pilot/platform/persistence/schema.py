"""
Centralized SQLite schema definitions for the persistence layer.

This module contains the canonical table definitions and indices used by
SQLite repositories.
"""

from __future__ import annotations

import sqlite3

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
    """,
    """
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
    """,
    """
    CREATE TABLE IF NOT EXISTS message_preferences (
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
    """,
    """
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
    """,
    """
    CREATE TABLE IF NOT EXISTS scheduled_messages (
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
    """,
    """
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
    """,
    """
    CREATE TABLE IF NOT EXISTS message_logs (
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
    """,
    """
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
    """,
    """
    CREATE TABLE IF NOT EXISTS message_endpoints (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        channel TEXT NOT NULL,
        destination TEXT NOT NULL,
        verified INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, channel, destination)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS message_threads (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        channel TEXT NOT NULL,
        endpoint_id TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, channel, endpoint_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS message_thread_participants (
        id TEXT PRIMARY KEY,
        thread_id TEXT NOT NULL,
        participant_type TEXT NOT NULL,
        participant_id TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS message_thread_messages (
        id TEXT PRIMARY KEY,
        thread_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        channel TEXT NOT NULL,
        direction TEXT NOT NULL,
        body TEXT NOT NULL,
        attachments_json TEXT NOT NULL,
        metadata_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mobility_reminder_settings (
        user_id TEXT PRIMARY KEY,
        updated_at TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
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
    """,
    """
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
    """,
    """
    CREATE TABLE IF NOT EXISTS clinical_cards (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        format TEXT NOT NULL,
        payload_json TEXT NOT NULL
    )
    """,
    """
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
    """,
    """
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
    """,
    """
    CREATE TABLE IF NOT EXISTS event_reaction_executions (
        event_id TEXT NOT NULL,
        handler_name TEXT NOT NULL,
        status TEXT NOT NULL,
        started_at TEXT,
        completed_at TEXT,
        failure_count INTEGER NOT NULL DEFAULT 0,
        last_error TEXT,
        payload_hash TEXT,
        event_version TEXT,
        ordering_scope TEXT NOT NULL DEFAULT 'none',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (event_id, handler_name)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS case_snapshot_sections (
        user_id TEXT NOT NULL,
        section_key TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        schema_version TEXT NOT NULL,
        projection_version TEXT NOT NULL,
        source_event_cursor TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (user_id, section_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS event_handler_cursors (
        handler_name TEXT NOT NULL,
        scope_key TEXT NOT NULL,
        last_event_id TEXT,
        last_event_time TEXT,
        updated_at TEXT NOT NULL,
        PRIMARY KEY (handler_name, scope_key)
    )
    """,
)

INDEX_STATEMENTS: tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS idx_reminders_user_time ON reminder_events(user_id, scheduled_at)",
    "CREATE INDEX IF NOT EXISTS idx_reminder_definitions_user_active ON reminder_definitions(user_id, active, updated_at)",
    "CREATE INDEX IF NOT EXISTS idx_reminder_occurrences_user_status_time ON reminder_occurrences(user_id, status, trigger_at)",
    "CREATE INDEX IF NOT EXISTS idx_medication_regimens_user_active ON medication_regimens(user_id, active)",
    "CREATE INDEX IF NOT EXISTS idx_meal_records_user_captured ON meal_records(user_id, captured_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_meal_candidates_user_status ON meal_candidates(user_id, confirmation_status, captured_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_biomarker_readings_user_name_measured ON biomarker_readings(user_id, name, measured_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_scheduled_notifications_user_status_trigger ON scheduled_notifications(user_id, status, trigger_at)",
    "CREATE INDEX IF NOT EXISTS idx_scheduled_messages_user_status_trigger ON scheduled_messages(user_id, status, trigger_at)",
    "CREATE INDEX IF NOT EXISTS idx_medication_adherence_events_user_status_scheduled ON medication_adherence_events(user_id, status, scheduled_at)",
    "CREATE INDEX IF NOT EXISTS idx_symptom_checkins_user_recorded ON symptom_checkins(user_id, recorded_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_workflow_timeline_events_correlation ON workflow_timeline_events(correlation_id)",
    "CREATE INDEX IF NOT EXISTS idx_event_reaction_executions_status ON event_reaction_executions(status, started_at)",
    "CREATE INDEX IF NOT EXISTS idx_reminder_occurrences_definition ON reminder_occurrences(reminder_definition_id)",
    "CREATE INDEX IF NOT EXISTS idx_reminder_actions_occurrence ON reminder_actions(occurrence_id)",
    "CREATE INDEX IF NOT EXISTS idx_scheduled_notifications_occurrence ON scheduled_notifications(occurrence_id)",
    "CREATE INDEX IF NOT EXISTS idx_scheduled_messages_occurrence ON scheduled_messages(occurrence_id)",
    "CREATE INDEX IF NOT EXISTS idx_event_reaction_executions_ordering ON event_reaction_executions(ordering_scope, status)",
)


def ensure_sqlite_column(cur: sqlite3.Cursor, table: str, column: str, definition: str) -> None:
    """Add a column to a table if it does not exist."""
    rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {str(row[1]) for row in rows}
    if column not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def migrate_schema(cur: sqlite3.Cursor) -> None:
    """Execute all schema migrations for the SQLite database."""
    ensure_sqlite_column(cur, "medication_regimens", "canonical_name", "TEXT")
    ensure_sqlite_column(
        cur,
        "medication_regimens",
        "frequency_type",
        "TEXT NOT NULL DEFAULT 'fixed_time'",
    )
    ensure_sqlite_column(
        cur,
        "medication_regimens",
        "frequency_times_per_day",
        "INTEGER NOT NULL DEFAULT 1",
    )
    ensure_sqlite_column(
        cur,
        "medication_regimens",
        "time_rules_json",
        "TEXT NOT NULL DEFAULT '[]'",
    )
    ensure_sqlite_column(cur, "medication_regimens", "instructions_text", "TEXT")
    ensure_sqlite_column(
        cur,
        "medication_regimens",
        "source_type",
        "TEXT NOT NULL DEFAULT 'manual'",
    )
    ensure_sqlite_column(cur, "medication_regimens", "source_filename", "TEXT")
    ensure_sqlite_column(cur, "medication_regimens", "source_hash", "TEXT")
    ensure_sqlite_column(cur, "medication_regimens", "start_date", "TEXT")
    ensure_sqlite_column(cur, "medication_regimens", "end_date", "TEXT")
    ensure_sqlite_column(
        cur,
        "medication_regimens",
        "timezone",
        "TEXT NOT NULL DEFAULT 'Asia/Singapore'",
    )
    ensure_sqlite_column(cur, "medication_regimens", "parse_confidence", "REAL")
    ensure_sqlite_column(cur, "reminder_events", "reminder_definition_id", "TEXT")
    ensure_sqlite_column(cur, "reminder_events", "occurrence_id", "TEXT")
    ensure_sqlite_column(cur, "reminder_events", "regimen_id", "TEXT")
    ensure_sqlite_column(cur, "scheduled_notifications", "occurrence_id", "TEXT")
    ensure_sqlite_column(cur, "scheduled_messages", "occurrence_id", "TEXT")
    ensure_sqlite_column(cur, "notification_logs", "occurrence_id", "TEXT")
    ensure_sqlite_column(cur, "message_logs", "occurrence_id", "TEXT")
    ensure_sqlite_column(cur, "event_reaction_executions", "next_retry_at", "TEXT")

    # Legacy table migrations
    cur.execute("SELECT COUNT(*) FROM message_preferences")
    message_pref_count = int(cur.fetchone()[0])
    cur.execute("PRAGMA table_info(reminder_notification_preferences)")
    if cur.fetchone():  # Check if legacy table exists
        cur.execute("SELECT COUNT(*) FROM reminder_notification_preferences")
        legacy_pref_count = int(cur.fetchone()[0])
        if message_pref_count == 0 and legacy_pref_count > 0:
            cur.execute(
                """
                INSERT INTO message_preferences
                (id, user_id, scope_type, scope_key, channel, offset_minutes, enabled, created_at, updated_at)
                SELECT id, user_id, scope_type, scope_key, channel, offset_minutes, enabled, created_at, updated_at
                FROM reminder_notification_preferences
                """
            )

    cur.execute("SELECT COUNT(*) FROM message_endpoints")
    message_endpoint_count = int(cur.fetchone()[0])
    cur.execute("PRAGMA table_info(reminder_notification_endpoints)")
    if cur.fetchone():
        cur.execute("SELECT COUNT(*) FROM reminder_notification_endpoints")
        legacy_endpoint_count = int(cur.fetchone()[0])
        if message_endpoint_count == 0 and legacy_endpoint_count > 0:
            cur.execute(
                """
                INSERT INTO message_endpoints
                (id, user_id, channel, destination, verified, created_at, updated_at)
                SELECT id, user_id, channel, destination, verified, created_at, updated_at
                FROM reminder_notification_endpoints
                """
            )

    cur.execute("SELECT COUNT(*) FROM scheduled_messages")
    message_sched_count = int(cur.fetchone()[0])
    cur.execute("PRAGMA table_info(scheduled_notifications)")
    if cur.fetchone():
        cur.execute("SELECT COUNT(*) FROM scheduled_notifications")
        legacy_sched_count = int(cur.fetchone()[0])
        if message_sched_count == 0 and legacy_sched_count > 0:
            cur.execute(
                """
                INSERT INTO scheduled_messages
                (id, reminder_id, occurrence_id, user_id, channel, trigger_at, offset_minutes, preference_id,
                 status, attempt_count, next_attempt_at, queued_at, delivered_at, last_error, payload_json,
                 idempotency_key, created_at, updated_at)
                SELECT id, reminder_id, occurrence_id, user_id, channel, trigger_at, offset_minutes, preference_id,
                       status, attempt_count, next_attempt_at, queued_at, delivered_at, last_error, payload_json,
                       idempotency_key, created_at, updated_at
                FROM scheduled_notifications
                """
            )

    cur.execute("SELECT COUNT(*) FROM message_logs")
    message_log_count = int(cur.fetchone()[0])
    cur.execute("PRAGMA table_info(notification_logs)")
    if cur.fetchone():
        cur.execute("SELECT COUNT(*) FROM notification_logs")
        legacy_log_count = int(cur.fetchone()[0])
        if message_log_count == 0 and legacy_log_count > 0:
            cur.execute(
                """
                INSERT INTO message_logs
                (id, scheduled_notification_id, reminder_id, occurrence_id, user_id, channel, attempt_number,
                 event_type, error_message, metadata_json, created_at)
                SELECT id, scheduled_notification_id, reminder_id, occurrence_id, user_id, channel, attempt_number,
                       event_type, error_message, metadata_json, created_at
                FROM notification_logs
                """
            )
