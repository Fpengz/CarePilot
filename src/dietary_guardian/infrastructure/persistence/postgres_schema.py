from __future__ import annotations

from collections.abc import Iterable
import os
import sys
from typing import Any


APP_SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS medication_regimens (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        medication_name TEXT NOT NULL,
        dosage_text TEXT NOT NULL,
        timing_type TEXT NOT NULL,
        offset_minutes INTEGER NOT NULL,
        slot_scope_json JSONB NOT NULL,
        fixed_time TEXT,
        max_daily_doses INTEGER NOT NULL,
        active BOOLEAN NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reminder_events (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        reminder_type TEXT NOT NULL DEFAULT 'medication',
        title TEXT NOT NULL DEFAULT 'Medication Reminder',
        body TEXT,
        medication_name TEXT NOT NULL,
        scheduled_at TIMESTAMPTZ NOT NULL,
        slot TEXT,
        dosage_text TEXT NOT NULL,
        status TEXT NOT NULL,
        meal_confirmation TEXT NOT NULL,
        sent_at TIMESTAMPTZ,
        ack_at TIMESTAMPTZ
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS meal_records (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        captured_at TIMESTAMPTZ NOT NULL,
        source TEXT NOT NULL,
        meal_state_json JSONB NOT NULL,
        analysis_version TEXT NOT NULL,
        multi_item_count INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS biomarker_readings (
        id BIGSERIAL PRIMARY KEY,
        user_id TEXT NOT NULL,
        name TEXT NOT NULL,
        value DOUBLE PRECISION NOT NULL,
        unit TEXT,
        reference_range TEXT,
        measured_at TIMESTAMPTZ,
        source_doc_id TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS recommendation_records (
        id BIGSERIAL PRIMARY KEY,
        user_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        payload_json JSONB NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS suggestion_records (
        suggestion_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        payload_json JSONB NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS health_profiles (
        user_id TEXT PRIMARY KEY,
        updated_at TIMESTAMPTZ NOT NULL,
        payload_json JSONB NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS health_profile_onboarding_states (
        user_id TEXT PRIMARY KEY,
        updated_at TIMESTAMPTZ NOT NULL,
        payload_json JSONB NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS meal_catalog (
        meal_id TEXT PRIMARY KEY,
        locale TEXT NOT NULL,
        slot TEXT NOT NULL,
        active BOOLEAN NOT NULL,
        payload_json JSONB NOT NULL
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
        created_at TIMESTAMPTZ NOT NULL,
        metadata_json JSONB NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS preference_snapshots (
        user_id TEXT PRIMARY KEY,
        updated_at TIMESTAMPTZ NOT NULL,
        payload_json JSONB NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS alert_outbox (
        alert_id TEXT NOT NULL,
        sink TEXT NOT NULL,
        type TEXT NOT NULL,
        severity TEXT NOT NULL,
        payload_json JSONB NOT NULL,
        correlation_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        state TEXT NOT NULL,
        attempt_count INTEGER NOT NULL,
        next_attempt_at TIMESTAMPTZ NOT NULL,
        last_error TEXT,
        lease_owner TEXT,
        lease_until TIMESTAMPTZ,
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
        enabled BOOLEAN NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        UNIQUE(user_id, scope_type, scope_key, channel, offset_minutes)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS scheduled_notifications (
        id TEXT PRIMARY KEY,
        reminder_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        channel TEXT NOT NULL,
        trigger_at TIMESTAMPTZ NOT NULL,
        offset_minutes INTEGER NOT NULL,
        preference_id TEXT,
        status TEXT NOT NULL,
        attempt_count INTEGER NOT NULL,
        next_attempt_at TIMESTAMPTZ,
        queued_at TIMESTAMPTZ,
        delivered_at TIMESTAMPTZ,
        last_error TEXT,
        payload_json JSONB NOT NULL,
        idempotency_key TEXT NOT NULL UNIQUE,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notification_logs (
        id TEXT PRIMARY KEY,
        scheduled_notification_id TEXT NOT NULL,
        reminder_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        channel TEXT NOT NULL,
        attempt_number INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        error_message TEXT,
        metadata_json JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reminder_notification_endpoints (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        channel TEXT NOT NULL,
        destination TEXT NOT NULL,
        verified BOOLEAN NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        UNIQUE(user_id, channel)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mobility_reminder_settings (
        user_id TEXT PRIMARY KEY,
        updated_at TIMESTAMPTZ NOT NULL,
        payload_json JSONB NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS medication_adherence_events (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        regimen_id TEXT NOT NULL,
        reminder_id TEXT,
        status TEXT NOT NULL,
        scheduled_at TIMESTAMPTZ NOT NULL,
        taken_at TIMESTAMPTZ,
        source TEXT NOT NULL,
        metadata_json JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS symptom_checkins (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        recorded_at TIMESTAMPTZ NOT NULL,
        severity INTEGER NOT NULL,
        symptom_codes_json JSONB NOT NULL,
        free_text TEXT,
        context_json JSONB NOT NULL,
        safety_json JSONB NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS clinical_cards (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        format TEXT NOT NULL,
        payload_json JSONB NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_role_policies (
        id TEXT PRIMARY KEY,
        role TEXT NOT NULL,
        agent_id TEXT NOT NULL,
        tool_name TEXT NOT NULL,
        effect TEXT NOT NULL,
        conditions_json JSONB NOT NULL,
        priority INTEGER NOT NULL,
        enabled BOOLEAN NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS workflow_contract_snapshots (
        id TEXT PRIMARY KEY,
        version INTEGER NOT NULL UNIQUE,
        contract_hash TEXT NOT NULL,
        source TEXT NOT NULL,
        workflows_json JSONB NOT NULL,
        agents_json JSONB NOT NULL,
        created_by TEXT,
        created_at TIMESTAMPTZ NOT NULL
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
        payload_json JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_reminders_user_time ON reminder_events(user_id, scheduled_at)",
    "CREATE INDEX IF NOT EXISTS idx_meals_user_time ON meal_records(user_id, captured_at)",
    "CREATE INDEX IF NOT EXISTS idx_biomarkers_user_time_name ON biomarker_readings(user_id, measured_at, name)",
    "CREATE INDEX IF NOT EXISTS idx_suggestions_user_time ON suggestion_records(user_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_health_profiles_updated_at ON health_profiles(updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_health_profile_onboarding_updated_at ON health_profile_onboarding_states(updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_meal_catalog_locale_slot ON meal_catalog(locale, slot)",
    "CREATE INDEX IF NOT EXISTS idx_recommendation_interactions_user_time ON recommendation_interactions(user_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_preference_snapshots_updated_at ON preference_snapshots(updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_alert_outbox_next_attempt ON alert_outbox(state, next_attempt_at)",
    "CREATE INDEX IF NOT EXISTS idx_reminder_notification_preferences_user_scope ON reminder_notification_preferences(user_id, scope_type, scope_key)",
    "CREATE INDEX IF NOT EXISTS idx_scheduled_notifications_due ON scheduled_notifications(status, trigger_at, next_attempt_at)",
    "CREATE INDEX IF NOT EXISTS idx_scheduled_notifications_reminder_id ON scheduled_notifications(reminder_id)",
    "CREATE INDEX IF NOT EXISTS idx_notification_logs_reminder_created ON notification_logs(reminder_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_reminder_notification_endpoints_user_channel ON reminder_notification_endpoints(user_id, channel)",
    "CREATE INDEX IF NOT EXISTS idx_adherence_user_time ON medication_adherence_events(user_id, scheduled_at)",
    "CREATE INDEX IF NOT EXISTS idx_symptom_checkins_user_time ON symptom_checkins(user_id, recorded_at)",
    "CREATE INDEX IF NOT EXISTS idx_clinical_cards_user_created ON clinical_cards(user_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_tool_role_policies_lookup ON tool_role_policies(role, agent_id, tool_name, enabled, priority DESC)",
    "CREATE INDEX IF NOT EXISTS idx_workflow_contract_snapshots_created ON workflow_contract_snapshots(created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_workflow_contract_snapshots_hash ON workflow_contract_snapshots(contract_hash)",
    "CREATE INDEX IF NOT EXISTS idx_workflow_timeline_corr_created ON workflow_timeline_events(correlation_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_workflow_timeline_user_created ON workflow_timeline_events(user_id, created_at)",
)

AUTH_SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS auth_users (
        user_id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        display_name TEXT NOT NULL,
        account_role TEXT NOT NULL,
        profile_mode TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_sessions (
        session_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        email TEXT NOT NULL,
        account_role TEXT NOT NULL,
        profile_mode TEXT NOT NULL,
        scopes_json JSONB NOT NULL,
        display_name TEXT NOT NULL,
        issued_at TIMESTAMPTZ NOT NULL,
        subject_user_id TEXT NOT NULL,
        active_household_id TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_login_failures (
        email TEXT PRIMARY KEY,
        failed_count INTEGER NOT NULL,
        window_started_at TIMESTAMPTZ,
        lockout_until TIMESTAMPTZ
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_audit_events (
        event_id TEXT PRIMARY KEY,
        event_type TEXT NOT NULL,
        email TEXT NOT NULL,
        user_id TEXT,
        created_at TIMESTAMPTZ NOT NULL,
        metadata_json JSONB NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_auth_audit_created_at ON auth_audit_events(created_at DESC)",
)

HOUSEHOLD_SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS households (
        household_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        owner_user_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS household_members (
        household_id TEXT NOT NULL,
        user_id TEXT NOT NULL UNIQUE,
        display_name TEXT NOT NULL,
        role TEXT NOT NULL,
        joined_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (household_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS household_invites (
        invite_id TEXT PRIMARY KEY,
        household_id TEXT NOT NULL,
        code TEXT NOT NULL UNIQUE,
        created_by_user_id TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        expires_at TIMESTAMPTZ NOT NULL,
        max_uses INTEGER NOT NULL,
        uses INTEGER NOT NULL DEFAULT 0,
        revoked_at TIMESTAMPTZ
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_household_members_user ON household_members(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_household_invites_code ON household_invites(code)",
)


def _execute_statements(conn: Any, statements: Iterable[str]) -> None:
    with conn.cursor() as cur:
        for statement in statements:
            cur.execute(statement)


def ensure_postgres_app_schema(conn: Any) -> None:
    _execute_statements(conn, APP_SCHEMA_STATEMENTS)


def ensure_postgres_auth_schema(conn: Any) -> None:
    _execute_statements(conn, AUTH_SCHEMA_STATEMENTS)


def ensure_postgres_household_schema(conn: Any) -> None:
    _execute_statements(conn, HOUSEHOLD_SCHEMA_STATEMENTS)


def _load_psycopg_module() -> Any:
    try:
        import psycopg
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError("psycopg package is required to bootstrap PostgreSQL schema.") from exc
    return psycopg


def bootstrap_postgres_schema(dsn: str) -> None:
    psycopg = _load_psycopg_module()
    with psycopg.connect(dsn, autocommit=True) as conn:
        ensure_postgres_auth_schema(conn)
        ensure_postgres_household_schema(conn)
        ensure_postgres_app_schema(conn)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    dsn = args[0] if args else os.environ.get("POSTGRES_DSN")
    if not dsn:
        raise SystemExit("POSTGRES_DSN must be provided as an argument or environment variable.")
    bootstrap_postgres_schema(dsn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
