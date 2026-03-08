from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, cast
from uuid import uuid4

from dietary_guardian.config.settings import Settings
from dietary_guardian.infrastructure.auth.demo_defaults import build_demo_user_seeds
from dietary_guardian.infrastructure.auth.in_memory import AuthUserRecord, PasswordHasher
from dietary_guardian.infrastructure.persistence.postgres_schema import ensure_postgres_auth_schema
from dietary_guardian.models.identity import AccountRole, ProfileMode
from dietary_guardian.services.authorization import scopes_for_account_role


def _load_psycopg_module() -> Any:
    try:
        import psycopg
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError(
            "psycopg package is required for AUTH_STORE_BACKEND=postgres. Run `uv sync` after updating dependencies."
        ) from exc
    return psycopg


class PostgresAuthStore:
    def __init__(self, settings: Settings, *, dsn: str) -> None:
        self._hasher = PasswordHasher(settings.auth_password_hash_scheme)
        self._demo_defaults = build_demo_user_seeds(settings)
        self._session_ttl_seconds = int(settings.auth_session_ttl_seconds)
        self._login_max_failed_attempts = int(settings.auth_login_max_failed_attempts)
        self._login_failure_window_seconds = int(settings.auth_login_failure_window_seconds)
        self._login_lockout_seconds = int(settings.auth_login_lockout_seconds)
        self._auth_audit_events_max_entries = int(settings.auth_audit_events_max_entries)
        self._psycopg = _load_psycopg_module()
        self._dsn = dsn
        self._jsonb = self._psycopg.types.json.Jsonb
        with self._connect() as conn:
            ensure_postgres_auth_schema(conn)
        if settings.auth_seed_demo_users:
            self._seed_defaults()

    def _connect(self) -> Any:
        return self._psycopg.connect(self._dsn, autocommit=True)

    def _seed_defaults(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            for user_id, email, display_name, account_role, profile_mode, password in self._demo_defaults:
                cur.execute(
                    """
                    INSERT INTO auth_users (user_id, email, display_name, account_role, profile_mode, password_hash, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (email) DO NOTHING
                    """,
                    (
                        user_id,
                        email,
                        display_name,
                        account_role,
                        profile_mode,
                        self._hasher.hash(password),
                        datetime.now(timezone.utc),
                    ),
                )

    def _row_to_user(self, row: Any) -> AuthUserRecord:
        return AuthUserRecord(
            user_id=str(row[0]),
            email=str(row[1]),
            display_name=str(row[2]),
            account_role=cast(AccountRole, str(row[3])),
            profile_mode=cast(ProfileMode, str(row[4])),
            password_hash=str(row[5]),
        )

    def authenticate(self, email: str, password: str) -> AuthUserRecord | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, email, display_name, account_role, profile_mode, password_hash FROM auth_users WHERE email = %s",
                (email,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        user = self._row_to_user(row)
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
        user = AuthUserRecord(
            user_id=f"user_{uuid4().hex[:12]}",
            email=normalized_email,
            display_name=display_name,
            account_role=account_role,
            profile_mode=profile_mode,
            password_hash=self._hasher.hash(password),
        )
        try:
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO auth_users (user_id, email, display_name, account_role, profile_mode, password_hash, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user.user_id,
                        user.email,
                        user.display_name,
                        user.account_role,
                        user.profile_mode,
                        user.password_hash,
                        datetime.now(timezone.utc),
                    ),
                )
        except self._psycopg.IntegrityError:
            return None
        return user

    def _read_failure_state(self, email: str) -> dict[str, Any] | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT failed_count, window_started_at, lockout_until FROM auth_login_failures WHERE email = %s",
                (email,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return {
            "failed_count": int(row[0]),
            "window_started_at": row[1].isoformat() if row[1] is not None else None,
            "lockout_until": row[2].isoformat() if row[2] is not None else None,
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
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute("DELETE FROM auth_login_failures WHERE email = %s", (email,))
            return False
        if lockout_until.tzinfo is None:
            lockout_until = lockout_until.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= lockout_until.astimezone(timezone.utc):
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE auth_login_failures
                    SET failed_count = 0, window_started_at = NULL, lockout_until = NULL
                    WHERE email = %s
                    """,
                    (email,),
                )
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
        lockout_until: datetime | None = None
        if failed_count >= self._login_max_failed_attempts:
            lockout_until = now + timedelta(seconds=self._login_lockout_seconds)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO auth_login_failures (email, failed_count, window_started_at, lockout_until)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE SET
                  failed_count = EXCLUDED.failed_count,
                  window_started_at = EXCLUDED.window_started_at,
                  lockout_until = EXCLUDED.lockout_until
                """,
                (email, failed_count, now if reset_window else state.get("window_started_at"), lockout_until),
            )
        return lockout_until is not None

    def record_login_success(self, email: str) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM auth_login_failures WHERE email = %s", (email,))

    def append_auth_audit_event(
        self,
        *,
        event_type: str,
        email: str,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO auth_audit_events (event_id, event_type, email, user_id, created_at, metadata_json)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid4()),
                    event_type,
                    email,
                    user_id,
                    datetime.now(timezone.utc),
                    self._jsonb(metadata or {}),
                ),
            )
            cur.execute("SELECT COUNT(*) FROM auth_audit_events")
            row = cur.fetchone()
            count = int(row[0]) if row is not None else 0
            if count > self._auth_audit_events_max_entries:
                excess = count - self._auth_audit_events_max_entries
                cur.execute(
                    """
                    DELETE FROM auth_audit_events
                    WHERE event_id IN (
                        SELECT event_id FROM auth_audit_events
                        ORDER BY created_at ASC
                        LIMIT %s
                    )
                    """,
                    (excess,),
                )

    def list_auth_audit_events(self, *, limit: int = 50) -> list[dict[str, Any]]:
        bounded = max(1, min(int(limit), 200))
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT event_id, event_type, email, user_id, created_at, metadata_json
                FROM auth_audit_events
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (bounded,),
            )
            rows = cur.fetchall()
        return [
            {
                "event_id": str(row[0]),
                "event_type": str(row[1]),
                "email": str(row[2]),
                "user_id": (str(row[3]) if row[3] is not None else None),
                "created_at": row[4].isoformat(),
                "metadata": cast(dict[str, Any], row[5]),
            }
            for row in rows
        ]

    def update_user_profile(
        self,
        *,
        user_id: str,
        display_name: str | None = None,
        profile_mode: ProfileMode | None = None,
    ) -> AuthUserRecord | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, email, display_name, account_role, profile_mode, password_hash FROM auth_users WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            current = self._row_to_user(row)
            new_display_name = display_name if display_name is not None else current.display_name
            new_profile_mode = profile_mode if profile_mode is not None else current.profile_mode
            cur.execute(
                "UPDATE auth_users SET display_name = %s, profile_mode = %s WHERE user_id = %s",
                (new_display_name, new_profile_mode, user_id),
            )
            cur.execute(
                "UPDATE auth_sessions SET display_name = %s, profile_mode = %s WHERE user_id = %s",
                (new_display_name, new_profile_mode, user_id),
            )
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
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, email, display_name, account_role, profile_mode, password_hash FROM auth_users WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
        if row is None:
            return (False, 0)
        user = self._row_to_user(row)
        if not self._hasher.verify(current_password, user.password_hash):
            return (False, 0)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE auth_users SET password_hash = %s WHERE user_id = %s",
                (self._hasher.hash(new_password), user_id),
            )
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
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO auth_sessions
                (session_id, user_id, email, account_role, profile_mode, scopes_json, display_name, issued_at, subject_user_id, active_household_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    email = EXCLUDED.email,
                    account_role = EXCLUDED.account_role,
                    profile_mode = EXCLUDED.profile_mode,
                    scopes_json = EXCLUDED.scopes_json,
                    display_name = EXCLUDED.display_name,
                    issued_at = EXCLUDED.issued_at,
                    subject_user_id = EXCLUDED.subject_user_id,
                    active_household_id = EXCLUDED.active_household_id
                """,
                (
                    session["session_id"],
                    session["user_id"],
                    session["email"],
                    session["account_role"],
                    session["profile_mode"],
                    self._jsonb(session["scopes"]),
                    session["display_name"],
                    datetime.fromisoformat(str(session["issued_at"])),
                    session["subject_user_id"],
                    session["active_household_id"],
                ),
            )
        return session

    def _row_to_session(self, row: Any) -> dict[str, Any]:
        scopes_raw = row[5]
        if not isinstance(scopes_raw, list) or not all(isinstance(item, str) for item in scopes_raw):
            raise ValueError("invalid scopes_json")
        return {
            "session_id": str(row[0]),
            "user_id": str(row[1]),
            "email": str(row[2]),
            "account_role": str(row[3]),
            "profile_mode": str(row[4]),
            "scopes": cast(list[str], scopes_raw),
            "display_name": str(row[6]),
            "issued_at": row[7].isoformat(),
            "subject_user_id": str(row[8]),
            "active_household_id": str(row[9]) if row[9] is not None else None,
        }

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT session_id, user_id, email, account_role, profile_mode, scopes_json,
                       display_name, issued_at, subject_user_id, active_household_id
                FROM auth_sessions
                WHERE session_id = %s
                """,
                (session_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        try:
            session = self._row_to_session(row)
        except (TypeError, ValueError):
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
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM auth_sessions WHERE session_id = %s", (session_id,))

    def list_sessions_for_user(self, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT session_id FROM auth_sessions WHERE user_id = %s ORDER BY issued_at DESC",
                (user_id,),
            )
            rows = cur.fetchall()
        items: list[dict[str, Any]] = []
        for row in rows:
            session = self.get_session(str(row[0]))
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
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT session_id FROM auth_sessions WHERE user_id = %s AND session_id != %s",
                (user_id, keep_session_id),
            )
            rows = cur.fetchall()
            session_ids = [str(row[0]) for row in rows]
            if not session_ids:
                return 0
            cur.execute(
                "DELETE FROM auth_sessions WHERE user_id = %s AND session_id != %s",
                (user_id, keep_session_id),
            )
        return len(session_ids)

    def set_active_household_for_session(
        self, session_id: str, *, active_household_id: str | None
    ) -> dict[str, Any] | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE auth_sessions SET active_household_id = %s WHERE session_id = %s",
                (active_household_id, session_id),
            )
        return self.get_session(session_id)

    def close(self) -> None:
        return None
