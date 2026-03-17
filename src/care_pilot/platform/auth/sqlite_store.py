"""
Implement SQLite-backed auth persistence.

This module provides auth storage backed by a SQLite database.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from threading import RLock
from typing import Any, cast
from uuid import uuid4

from care_pilot.features.profiles.domain.models import AccountRole, ProfileMode
from care_pilot.platform.auth.demo_defaults import build_demo_user_seeds
from care_pilot.platform.auth.in_memory import AuthUserRecord, PasswordHasher
from care_pilot.platform.observability.tooling.domain.authorization import (
    scopes_for_account_role,
)


class SQLiteAuthStore:
    def __init__(self, db_path: str, settings: Any) -> None:
        self._db_path = db_path
        self._lock = RLock()
        self._hasher = PasswordHasher(settings.auth.password_hash_scheme)
        self._session_ttl_seconds = int(settings.auth.session_ttl_seconds)
        self._login_max_failed_attempts = int(settings.auth.login_max_failed_attempts)
        self._login_failure_window_seconds = int(settings.auth.login_failure_window_seconds)
        self._login_lockout_seconds = int(settings.auth.login_lockout_seconds)

        self._init_db()
        if settings.auth.seed_demo_users:
            self._seed_defaults(settings)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL,
                    account_role TEXT NOT NULL,
                    profile_mode TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    email TEXT NOT NULL,
                    account_role TEXT NOT NULL,
                    profile_mode TEXT NOT NULL,
                    scopes_json TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    subject_user_id TEXT,
                    active_household_id TEXT,
                    FOREIGN KEY(user_id) REFERENCES auth_users(user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_audit_events (
                    event_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    email TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    metadata_json TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_login_failures (
                    email TEXT PRIMARY KEY,
                    failed_count INTEGER NOT NULL DEFAULT 0,
                    window_started_at TEXT,
                    lockout_until TEXT
                )
                """
            )

            # Handle migration for active_household_id if needed
            cursor = conn.execute("PRAGMA table_info(auth_sessions)")
            session_columns = [row["name"] for row in cursor.fetchall()]
            if "active_household_id" not in session_columns:
                conn.execute("ALTER TABLE auth_sessions ADD COLUMN active_household_id TEXT")

            # Handle migration for auth_audit_events if needed
            try:
                cursor = conn.execute("SELECT * FROM auth_audit_events LIMIT 0")
                audit_columns = [description[0] for description in cursor.description]
                if "created_at" not in audit_columns:
                    # Force recreation for local consistency
                    conn.execute("DROP TABLE auth_audit_events")
                    conn.execute(
                        """
                        CREATE TABLE auth_audit_events (
                            event_id TEXT PRIMARY KEY,
                            user_id TEXT,
                            email TEXT NOT NULL,
                            event_type TEXT NOT NULL,
                            occurred_at TEXT NOT NULL,
                            created_at TEXT NOT NULL,
                            metadata_json TEXT
                        )
                        """
                    )
                else:
                    # Basic column additions if needed
                    if "user_id" not in audit_columns:
                        conn.execute("ALTER TABLE auth_audit_events ADD COLUMN user_id TEXT")
                    if "email" not in audit_columns:
                        conn.execute("ALTER TABLE auth_audit_events ADD COLUMN email TEXT")
                    if "occurred_at" not in audit_columns:
                        conn.execute("ALTER TABLE auth_audit_events ADD COLUMN occurred_at TEXT")
            except sqlite3.OperationalError:
                # Table doesn't exist, create it
                conn.execute(
                    """
                    CREATE TABLE auth_audit_events (
                        event_id TEXT PRIMARY KEY,
                        user_id TEXT,
                        email TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        occurred_at TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        metadata_json TEXT
                    )
                    """
                )

            conn.commit()

    def _seed_defaults(self, settings: Any) -> None:
        users = build_demo_user_seeds(settings)
        with self._lock, self._connect() as conn:
            for user_id, email, display_name, role, mode, password in users:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO auth_users (user_id, email, display_name, account_role, profile_mode, password_hash, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        email,
                        display_name,
                        role,
                        mode,
                        self._hasher.hash(password),
                        datetime.now(UTC).isoformat(),
                    ),
                )
            conn.commit()

    def authenticate(self, email: str, password: str) -> AuthUserRecord | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT user_id, email, display_name, account_role, profile_mode, password_hash FROM auth_users WHERE email = ?",
                (email,),
            ).fetchone()

        if row and self._hasher.verify(password, row["password_hash"]):
            return AuthUserRecord(
                user_id=row["user_id"],
                email=row["email"],
                display_name=row["display_name"],
                account_role=row["account_role"],
                profile_mode=row["profile_mode"],
                password_hash=row["password_hash"],
            )
        return None

    def create_user(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        account_role: AccountRole = "member",
        profile_mode: ProfileMode = "self",
    ) -> AuthUserRecord | None:
        normalized_email = email.strip().lower()
        try:
            user = AuthUserRecord(
                user_id=f"user_{uuid4().hex[:12]}",
                email=normalized_email,
                display_name=display_name,
                account_role=account_role,
                profile_mode=profile_mode,
                password_hash=self._hasher.hash(password),
            )
            with self._lock, self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO auth_users (user_id, email, display_name, account_role, profile_mode, password_hash, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user.user_id,
                        user.email,
                        user.display_name,
                        user.account_role,
                        user.profile_mode,
                        user.password_hash,
                        datetime.now(UTC).isoformat(),
                    ),
                )
                conn.commit()
            return user
        except sqlite3.IntegrityError:
            return None

    def _read_failure_state(self, email: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT failed_count, window_started_at, lockout_until FROM auth_login_failures WHERE email = ?",
                (email,),
            ).fetchone()
        if row is None:
            return None
        return {
            "failed_count": int(row["failed_count"]),
            "window_started_at": row["window_started_at"],
            "lockout_until": row["lockout_until"],
        }

    def is_login_locked(self, email: str) -> bool:
        state = self._read_failure_state(email)
        if not state:
            return False
        lockout_until_raw = state.get("lockout_until")
        if not isinstance(lockout_until_raw, str):
            return False
        try:
            lockout_until = datetime.fromisoformat(lockout_until_raw)
        except ValueError:
            with self._lock, self._connect() as conn:
                conn.execute("DELETE FROM auth_login_failures WHERE email = ?", (email,))
                conn.commit()
            return False
        if lockout_until.tzinfo is None:
            lockout_until = lockout_until.replace(tzinfo=UTC)
        if datetime.now(UTC) >= lockout_until.astimezone(UTC):
            with self._lock, self._connect() as conn:
                conn.execute(
                    "UPDATE auth_login_failures SET failed_count = 0, window_started_at = NULL, lockout_until = NULL WHERE email = ?",
                    (email,),
                )
                conn.commit()
            return False
        return True

    def record_login_failure(self, email: str) -> bool:
        now = datetime.now(UTC)
        state = self._read_failure_state(email) or {
            "failed_count": 0,
            "window_started_at": None,
            "lockout_until": None,
        }

        window_started_raw = state.get("window_started_at")
        reset_window = True
        if isinstance(window_started_raw, str):
            try:
                window_started = datetime.fromisoformat(window_started_raw)
                if window_started.tzinfo is None:
                    window_started = window_started.replace(tzinfo=UTC)
                reset_window = (
                    now - window_started.astimezone(UTC)
                ).total_seconds() > self._login_failure_window_seconds
            except ValueError:
                reset_window = True

        if reset_window:
            failed_count = 1
            window_started_at = now.isoformat()
        else:
            failed_count = int(cast(int, state["failed_count"])) + 1
            window_started_at = str(state["window_started_at"])

        lockout_until = None
        if failed_count >= self._login_max_failed_attempts:
            lockout_until = (now + timedelta(seconds=self._login_lockout_seconds)).isoformat()

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO auth_login_failures (email, failed_count, window_started_at, lockout_until)
                VALUES (?, ?, ?, ?)
                """,
                (email, failed_count, window_started_at, lockout_until),
            )
            conn.commit()
        return lockout_until is not None

    def record_login_success(self, email: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM auth_login_failures WHERE email = ?", (email,))
            conn.commit()

    def append_auth_audit_event(
        self,
        *,
        event_type: str,
        email: str,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now_iso = datetime.now(UTC).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO auth_audit_events (event_id, user_id, email, event_type, occurred_at, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    user_id,
                    email,
                    event_type,
                    now_iso,
                    now_iso,
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()

    def list_auth_audit_events(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                "SELECT event_id, user_id, email, event_type, occurred_at, metadata_json FROM auth_audit_events ORDER BY occurred_at DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()

        return [
            {
                "event_id": row["event_id"],
                "user_id": row["user_id"],
                "email": row["email"],
                "event_type": row["event_type"],
                "created_at": row["occurred_at"],
                "metadata": json.loads(row["metadata_json"] or "{}"),
            }
            for row in rows
        ]

    def create_session(self, user: AuthUserRecord) -> dict[str, Any]:
        session_id = str(uuid4())
        session = {
            "session_id": session_id,
            "user_id": user.user_id,
            "email": user.email,
            "account_role": user.account_role,
            "profile_mode": user.profile_mode,
            "scopes": scopes_for_account_role(user.account_role),
            "display_name": user.display_name,
            "issued_at": datetime.now(UTC).isoformat(),
            "subject_user_id": user.user_id,
            "active_household_id": None,
        }
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO auth_sessions (session_id, user_id, email, account_role, profile_mode, scopes_json, display_name, issued_at, subject_user_id, active_household_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session["session_id"],
                    session["user_id"],
                    session["email"],
                    session["account_role"],
                    session["profile_mode"],
                    json.dumps(session["scopes"]),
                    session["display_name"],
                    session["issued_at"],
                    session["subject_user_id"],
                    session["active_household_id"],
                ),
            )
            conn.commit()
        return session

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT session_id, user_id, email, account_role, profile_mode, scopes_json, display_name, issued_at, subject_user_id, active_household_id FROM auth_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()

        if row is None:
            return None

        # Handle potential invalid JSON in scopes_json (as seen in some tests)
        try:
            scopes = json.loads(row["scopes_json"])
        except json.JSONDecodeError:
            self.destroy_session(session_id)
            return None

        session = {
            "session_id": row["session_id"],
            "user_id": row["user_id"],
            "email": row["email"],
            "account_role": row["account_role"],
            "profile_mode": row["profile_mode"],
            "scopes": scopes,
            "display_name": row["display_name"],
            "issued_at": row["issued_at"],
            "subject_user_id": row["subject_user_id"],
            "active_household_id": row["active_household_id"],
        }

        try:
            issued_at = datetime.fromisoformat(session["issued_at"])
            if issued_at.tzinfo is None:
                issued_at = issued_at.replace(tzinfo=UTC)
            age_seconds = (datetime.now(UTC) - issued_at.astimezone(UTC)).total_seconds()
            if age_seconds > self._session_ttl_seconds:
                self.destroy_session(session_id)
                return None
        except ValueError:
            self.destroy_session(session_id)
            return None

        return session

    def destroy_session(self, session_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM auth_sessions WHERE session_id = ?", (session_id,))
            conn.commit()

    def list_sessions_for_user(self, user_id: str) -> list[dict[str, Any]]:
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                "SELECT session_id, issued_at FROM auth_sessions WHERE user_id = ? ORDER BY issued_at DESC",
                (user_id,),
            )
            rows = cursor.fetchall()

        items: list[dict[str, Any]] = []
        for row in rows:
            resolved = self.get_session(row["session_id"])
            if resolved:
                items.append(resolved)
        return items

    def get_session_owner(self, session_id: str) -> str | None:
        session = self.get_session(session_id)
        return str(session["user_id"]) if session else None

    def revoke_other_sessions(self, user_id: str, *, keep_session_id: str) -> int:
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM auth_sessions WHERE user_id = ? AND session_id != ?",
                (user_id, keep_session_id),
            )
            count = cursor.rowcount
            conn.commit()
        return count

    def update_user_profile(
        self,
        user_id: str,
        *,
        display_name: str | None = None,
        profile_mode: ProfileMode | None = None,
    ) -> AuthUserRecord | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT user_id, email, display_name, account_role, profile_mode, password_hash FROM auth_users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if not row:
                return None

            new_display_name = display_name if display_name is not None else row["display_name"]
            new_profile_mode = profile_mode if profile_mode is not None else row["profile_mode"]

            conn.execute(
                "UPDATE auth_users SET display_name = ?, profile_mode = ? WHERE user_id = ?",
                (new_display_name, new_profile_mode, user_id),
            )
            conn.execute(
                "UPDATE auth_sessions SET display_name = ?, profile_mode = ? WHERE user_id = ?",
                (new_display_name, new_profile_mode, user_id),
            )
            conn.commit()

        return AuthUserRecord(
            user_id=row["user_id"],
            email=row["email"],
            display_name=new_display_name,
            account_role=row["account_role"],
            profile_mode=new_profile_mode,
            password_hash=row["password_hash"],
        )

    def change_user_password(
        self,
        *,
        user_id: str,
        current_password: str,
        new_password: str,
        keep_session_id: str,
    ) -> tuple[bool, int]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT password_hash FROM auth_users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if not row or not self._hasher.verify(current_password, row["password_hash"]):
                return (False, 0)

            new_hash = self._hasher.hash(new_password)
            conn.execute(
                "UPDATE auth_users SET password_hash = ? WHERE user_id = ?", (new_hash, user_id)
            )
            conn.commit()

        revoked_count = self.revoke_other_sessions(user_id, keep_session_id=keep_session_id)
        return (True, revoked_count)

    def set_active_household_for_session(
        self, session_id: str, *, active_household_id: str | None
    ) -> dict[str, Any] | None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE auth_sessions SET active_household_id = ? WHERE session_id = ?",
                (active_household_id, session_id),
            )
            conn.commit()
        return self.get_session(session_id)

    def close(self) -> None:
        pass
