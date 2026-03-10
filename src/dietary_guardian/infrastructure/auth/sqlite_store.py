import json
import sqlite3
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any, cast
from uuid import uuid4

from dietary_guardian.config.settings import Settings
from dietary_guardian.domain.identity.models import AccountRole, ProfileMode
from dietary_guardian.domain.tooling import scopes_for_account_role
from dietary_guardian.infrastructure.auth.demo_defaults import build_demo_user_seeds
from dietary_guardian.infrastructure.auth.in_memory import AuthUserRecord, PasswordHasher
from dietary_guardian.logging_config import get_logger

logger = get_logger(__name__)


class SQLiteAuthStore:
    def __init__(self, settings: Settings, db_path: str = "dietary_guardian_api.db") -> None:
        self._hasher = PasswordHasher(settings.auth.password_hash_scheme)
        self._demo_defaults = build_demo_user_seeds(settings)
        self._session_ttl_seconds = int(settings.auth.session_ttl_seconds)
        self._login_max_failed_attempts = int(settings.auth.login_max_failed_attempts)
        self._login_failure_window_seconds = int(settings.auth.login_failure_window_seconds)
        self._login_lockout_seconds = int(settings.auth.login_lockout_seconds)
        self._auth_audit_events_max_entries = int(settings.auth.audit_events_max_entries)
        self._lock = RLock()
        self._db_path = db_path
        self._init_db()
        if settings.auth.seed_demo_users:
            self._seed_defaults()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    account_role TEXT NOT NULL,
                    profile_mode TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
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
                    subject_user_id TEXT NOT NULL,
                    active_household_id TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_login_failures (
                    email TEXT PRIMARY KEY,
                    failed_count INTEGER NOT NULL,
                    window_started_at TEXT,
                    lockout_until TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_audit_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    email TEXT NOT NULL,
                    user_id TEXT,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_auth_audit_created_at ON auth_audit_events(created_at DESC)")
            session_columns = {
                str(row["name"])
                for row in cur.execute("PRAGMA table_info(auth_sessions)").fetchall()
            }
            if "active_household_id" not in session_columns:
                cur.execute("ALTER TABLE auth_sessions ADD COLUMN active_household_id TEXT")
            conn.commit()

    def _seed_defaults(self) -> None:
        with self._lock:
            with self._connect() as conn:
                for user_id, email, display_name, account_role, profile_mode, password in self._demo_defaults:
                    existing = conn.execute("SELECT 1 FROM auth_users WHERE email = ?", (email,)).fetchone()
                    if existing:
                        continue
                    conn.execute(
                        """
                        INSERT INTO auth_users (user_id, email, display_name, account_role, profile_mode, password_hash, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            user_id,
                            email,
                            display_name,
                            account_role,
                            profile_mode,
                            self._hasher.hash(password),
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                conn.commit()

    def _row_to_user(self, row: sqlite3.Row) -> AuthUserRecord:
        return AuthUserRecord(
            user_id=str(row["user_id"]),
            email=str(row["email"]),
            display_name=str(row["display_name"]),
            account_role=cast(AccountRole, str(row["account_role"])),
            profile_mode=cast(ProfileMode, str(row["profile_mode"])),
            password_hash=str(row["password_hash"]),
        )

    def authenticate(self, email: str, password: str) -> AuthUserRecord | None:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT user_id, email, display_name, account_role, profile_mode, password_hash FROM auth_users WHERE email = ?",
                    (email,),
                ).fetchone()
        if row is None:
            return None
        user = self._row_to_user(cast(sqlite3.Row, row))
        if not self._hasher.verify(password, user.password_hash):
            return None
        return user

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
        if not normalized_email:
            return None
        try:
            user = AuthUserRecord(
                user_id=f"user_{uuid4().hex[:12]}",
                email=normalized_email,
                display_name=display_name,
                account_role=account_role,
                profile_mode=profile_mode,
                password_hash=self._hasher.hash(password),
            )
            with self._lock:
                with self._connect() as conn:
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
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )
                    conn.commit()
            return user
        except sqlite3.IntegrityError:
            return None

    def _read_failure_state(self, email: str) -> dict[str, Any] | None:
        with self._lock:
            with self._connect() as conn:
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
            with self._lock:
                with self._connect() as conn:
                    conn.execute("DELETE FROM auth_login_failures WHERE email = ?", (email,))
                    conn.commit()
            return False
        if lockout_until.tzinfo is None:
            lockout_until = lockout_until.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= lockout_until.astimezone(timezone.utc):
            with self._lock:
                with self._connect() as conn:
                    conn.execute(
                        "UPDATE auth_login_failures SET failed_count = 0, window_started_at = NULL, lockout_until = NULL WHERE email = ?",
                        (email,),
                    )
                    conn.commit()
            return False
        return True

    def record_login_failure(self, email: str) -> bool:
        now = datetime.now(timezone.utc)
        state = self._read_failure_state(email) or {"failed_count": 0, "window_started_at": None, "lockout_until": None}
        reset_window = True
        window_started_raw = state.get("window_started_at")
        if isinstance(window_started_raw, str):
            try:
                window_started = datetime.fromisoformat(window_started_raw)
                if window_started.tzinfo is None:
                    window_started = window_started.replace(tzinfo=timezone.utc)
                reset_window = (
                    now - window_started.astimezone(timezone.utc)
                ).total_seconds() > self._login_failure_window_seconds
            except ValueError:
                reset_window = True
        failed_count_raw = state.get("failed_count", 0)
        failed_count = 0 if reset_window else (failed_count_raw if isinstance(failed_count_raw, int) else 0)
        failed_count += 1
        lockout_until: str | None = None
        if failed_count >= self._login_max_failed_attempts:
            lockout_until = (now + timedelta(seconds=self._login_lockout_seconds)).isoformat()
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO auth_login_failures (email, failed_count, window_started_at, lockout_until)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(email) DO UPDATE SET
                      failed_count=excluded.failed_count,
                      window_started_at=excluded.window_started_at,
                      lockout_until=excluded.lockout_until
                    """,
                    (email, failed_count, now.isoformat() if reset_window else state.get("window_started_at"), lockout_until),
                )
                conn.commit()
        return lockout_until is not None

    def record_login_success(self, email: str) -> None:
        with self._lock:
            with self._connect() as conn:
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
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO auth_audit_events (event_id, event_type, email, user_id, created_at, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        event_type,
                        email,
                        user_id,
                        datetime.now(timezone.utc).isoformat(),
                        json.dumps(metadata or {}),
                    ),
                )
                count_row = conn.execute("SELECT COUNT(*) AS c FROM auth_audit_events").fetchone()
                count = int(count_row["c"]) if count_row is not None else 0
                if count > self._auth_audit_events_max_entries:
                    excess = count - self._auth_audit_events_max_entries
                    conn.execute(
                        """
                        DELETE FROM auth_audit_events
                        WHERE event_id IN (
                            SELECT event_id FROM auth_audit_events
                            ORDER BY created_at ASC
                            LIMIT ?
                        )
                        """,
                        (excess,),
                    )
                conn.commit()

    def list_auth_audit_events(self, *, limit: int = 50) -> list[dict[str, Any]]:
        bounded = max(1, min(int(limit), 200))
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT event_id, event_type, email, user_id, created_at, metadata_json
                    FROM auth_audit_events
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (bounded,),
                ).fetchall()
        return [
            {
                "event_id": str(row["event_id"]),
                "event_type": str(row["event_type"]),
                "email": str(row["email"]),
                "user_id": (str(row["user_id"]) if row["user_id"] is not None else None),
                "created_at": str(row["created_at"]),
                "metadata": cast(dict[str, Any], json.loads(str(row["metadata_json"]))),
            }
            for row in rows
        ]

    def close(self) -> None:
        # No persistent sqlite connection is kept; nothing to close.
        return None

    def update_user_profile(
        self,
        *,
        user_id: str,
        display_name: str | None = None,
        profile_mode: ProfileMode | None = None,
    ) -> AuthUserRecord | None:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT user_id, email, display_name, account_role, profile_mode, password_hash FROM auth_users WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
        if row is None:
            return None
        current = self._row_to_user(cast(sqlite3.Row, row))
        new_display_name = display_name if display_name is not None else current.display_name
        new_profile_mode = profile_mode if profile_mode is not None else current.profile_mode
        with self._lock:
            with self._connect() as conn:
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
            user_id=current.user_id,
            email=current.email,
            display_name=str(new_display_name),
            account_role=current.account_role,
            profile_mode=cast(ProfileMode, str(new_profile_mode)),
            password_hash=current.password_hash,
        )

    def change_user_password(
        self,
        *,
        user_id: str,
        current_password: str,
        new_password: str,
        keep_session_id: str,
    ) -> tuple[bool, int]:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT user_id, email, display_name, account_role, profile_mode, password_hash FROM auth_users WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
        if row is None:
            return (False, 0)
        user = self._row_to_user(cast(sqlite3.Row, row))
        if not self._hasher.verify(current_password, user.password_hash):
            return (False, 0)
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE auth_users SET password_hash = ? WHERE user_id = ?",
                    (self._hasher.hash(new_password), user_id),
                )
                conn.commit()
        revoked_count = self.revoke_other_sessions(user_id, keep_session_id=keep_session_id)
        return (True, revoked_count)

    def create_session(self, user: AuthUserRecord) -> dict[str, Any]:
        session = {
            "session_id": str(uuid4()),
            "user_id": user.user_id,
            "email": user.email,
            "account_role": user.account_role,
            "profile_mode": user.profile_mode,
            "scopes": scopes_for_account_role(user.account_role),
            "display_name": user.display_name,
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "subject_user_id": user.user_id,
            "active_household_id": None,
        }
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO auth_sessions
                    (session_id, user_id, email, account_role, profile_mode, scopes_json, display_name, issued_at, subject_user_id, active_household_id)
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

    def _row_to_session(self, row: sqlite3.Row) -> dict[str, Any]:
        scopes_raw = json.loads(str(row["scopes_json"]))
        if not isinstance(scopes_raw, list) or not all(isinstance(item, str) for item in scopes_raw):
            raise ValueError("invalid scopes_json")
        return {
            "session_id": str(row["session_id"]),
            "user_id": str(row["user_id"]),
            "email": str(row["email"]),
            "account_role": str(row["account_role"]),
            "profile_mode": str(row["profile_mode"]),
            "scopes": cast(list[str], scopes_raw),
            "display_name": str(row["display_name"]),
            "issued_at": str(row["issued_at"]),
            "subject_user_id": str(row["subject_user_id"]),
            "active_household_id": (
                str(row["active_household_id"]) if row["active_household_id"] is not None else None
            ),
        }

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM auth_sessions WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
        if row is None:
            return None
        try:
            session = self._row_to_session(cast(sqlite3.Row, row))
        except (TypeError, ValueError, json.JSONDecodeError):
            self.destroy_session(session_id)
            return None
        issued_at_raw = session.get("issued_at")
        if not isinstance(issued_at_raw, str):
            self.destroy_session(session_id)
            return None
        try:
            issued_at = datetime.fromisoformat(issued_at_raw)
        except ValueError:
            self.destroy_session(session_id)
            return None
        if issued_at.tzinfo is None:
            issued_at = issued_at.replace(tzinfo=timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - issued_at.astimezone(timezone.utc)).total_seconds()
        if age_seconds > self._session_ttl_seconds:
            self.destroy_session(session_id)
            return None
        return session

    def destroy_session(self, session_id: str) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM auth_sessions WHERE session_id = ?", (session_id,))
                conn.commit()

    def list_sessions_for_user(self, user_id: str) -> list[dict[str, Any]]:
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM auth_sessions WHERE user_id = ? ORDER BY issued_at DESC",
                    (user_id,),
                ).fetchall()
        items: list[dict[str, Any]] = []
        for row in rows:
            session = self.get_session(str(row["session_id"]))
            if session is not None:
                items.append(session)
        return items

    def get_session_owner(self, session_id: str) -> str | None:
        session = self.get_session(session_id)
        if session is None:
            return None
        user_id = session.get("user_id")
        return str(user_id) if isinstance(user_id, str) else None

    def revoke_other_sessions(self, user_id: str, *, keep_session_id: str) -> int:
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT session_id FROM auth_sessions WHERE user_id = ? AND session_id != ?",
                    (user_id, keep_session_id),
                ).fetchall()
        session_ids = [str(row["session_id"]) for row in rows]
        if not session_ids:
            return 0
        with self._lock:
            with self._connect() as conn:
                conn.executemany("DELETE FROM auth_sessions WHERE session_id = ?", [(sid,) for sid in session_ids])
                conn.commit()
        return len(session_ids)

    def set_active_household_for_session(
        self, session_id: str, *, active_household_id: str | None
    ) -> dict[str, Any] | None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE auth_sessions SET active_household_id = ? WHERE session_id = ?",
                    (active_household_id, session_id),
                )
                conn.commit()
        return self.get_session(session_id)
