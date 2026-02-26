import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4


class SQLiteHouseholdStore:
    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS households (
                household_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                owner_user_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS household_members (
                household_id TEXT NOT NULL,
                user_id TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL,
                joined_at TEXT NOT NULL,
                PRIMARY KEY (household_id, user_id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS household_invites (
                invite_id TEXT PRIMARY KEY,
                household_id TEXT NOT NULL,
                code TEXT NOT NULL UNIQUE,
                created_by_user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                max_uses INTEGER NOT NULL,
                uses INTEGER NOT NULL DEFAULT 0,
                revoked_at TEXT
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_household_members_user ON household_members(user_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_household_invites_code ON household_invites(code)"
        )
        self._conn.commit()

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def get_household_for_user(self, user_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT h.household_id, h.name, h.owner_user_id, h.created_at
            FROM household_members m
            JOIN households h ON h.household_id = m.household_id
            WHERE m.user_id = ?
            """,
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "household_id": str(row["household_id"]),
            "name": str(row["name"]),
            "owner_user_id": str(row["owner_user_id"]),
            "created_at": str(row["created_at"]),
        }

    def get_household_by_id(self, household_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT household_id, name, owner_user_id, created_at FROM households WHERE household_id = ?",
            (household_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "household_id": str(row["household_id"]),
            "name": str(row["name"]),
            "owner_user_id": str(row["owner_user_id"]),
            "created_at": str(row["created_at"]),
        }

    def create_household(self, *, owner_user_id: str, owner_display_name: str, name: str) -> dict[str, Any]:
        now = self._now().isoformat()
        household_id = f"hh_{uuid4().hex[:12]}"
        with self._conn:
            self._conn.execute(
                "INSERT INTO households (household_id, name, owner_user_id, created_at) VALUES (?, ?, ?, ?)",
                (household_id, name, owner_user_id, now),
            )
            self._conn.execute(
                """
                INSERT INTO household_members (household_id, user_id, display_name, role, joined_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (household_id, owner_user_id, owner_display_name, "owner", now),
            )
        return {
            "household_id": household_id,
            "name": name,
            "owner_user_id": owner_user_id,
            "created_at": now,
        }

    def list_members(self, household_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT user_id, display_name, role, joined_at
            FROM household_members
            WHERE household_id = ?
            ORDER BY CASE role WHEN 'owner' THEN 0 ELSE 1 END, joined_at ASC
            """,
            (household_id,),
        ).fetchall()
        return [
            {
                "user_id": str(row["user_id"]),
                "display_name": str(row["display_name"]),
                "role": str(row["role"]),
                "joined_at": str(row["joined_at"]),
            }
            for row in rows
        ]

    def get_member_role(self, household_id: str, user_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT role FROM household_members WHERE household_id = ? AND user_id = ?",
            (household_id, user_id),
        ).fetchone()
        return None if row is None else str(row["role"])

    def rename_household(self, *, household_id: str, name: str) -> dict[str, Any] | None:
        with self._conn:
            cur = self._conn.execute(
                "UPDATE households SET name = ? WHERE household_id = ?",
                (name, household_id),
            )
        if int(cur.rowcount) == 0:
            return None
        return self.get_household_by_id(household_id)

    def create_invite(self, *, household_id: str, created_by_user_id: str) -> dict[str, Any]:
        now = self._now()
        invite_id = f"inv_{uuid4().hex[:12]}"
        code = f"hh_{secrets.token_urlsafe(6).rstrip('=')}"
        expires_at = (now + timedelta(days=7)).isoformat()
        max_uses = 10
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO household_invites (
                    invite_id, household_id, code, created_by_user_id, created_at, expires_at, max_uses, uses, revoked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL)
                """,
                (invite_id, household_id, code, created_by_user_id, now.isoformat(), expires_at, max_uses),
            )
        return {
            "invite_id": invite_id,
            "household_id": household_id,
            "code": code,
            "created_by_user_id": created_by_user_id,
            "created_at": now.isoformat(),
            "expires_at": expires_at,
            "max_uses": max_uses,
            "uses": 0,
        }

    def join_by_invite(self, *, code: str, user_id: str, display_name: str) -> tuple[dict[str, Any], bool] | None:
        invite = self._conn.execute(
            """
            SELECT invite_id, household_id, expires_at, max_uses, uses, revoked_at
            FROM household_invites
            WHERE code = ?
            """,
            (code,),
        ).fetchone()
        if invite is None:
            return None
        if invite["revoked_at"] is not None:
            return None
        try:
            expires_at = datetime.fromisoformat(str(invite["expires_at"]))
        except ValueError:
            return None
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if self._now() >= expires_at.astimezone(timezone.utc):
            return None

        household_id = str(invite["household_id"])
        existing = self.get_household_for_user(user_id)
        if existing is not None:
            return (existing, False)

        now = self._now().isoformat()
        uses = int(invite["uses"])
        max_uses = int(invite["max_uses"])
        if uses >= max_uses:
            return None

        with self._conn:
            self._conn.execute(
                """
                INSERT INTO household_members (household_id, user_id, display_name, role, joined_at)
                VALUES (?, ?, ?, 'member', ?)
                """,
                (household_id, user_id, display_name, now),
            )
            self._conn.execute(
                "UPDATE household_invites SET uses = uses + 1 WHERE invite_id = ?",
                (str(invite["invite_id"]),),
            )
        household = self._conn.execute(
            "SELECT household_id, name, owner_user_id, created_at FROM households WHERE household_id = ?",
            (household_id,),
        ).fetchone()
        if household is None:
            return None
        return (
            {
                "household_id": str(household["household_id"]),
                "name": str(household["name"]),
                "owner_user_id": str(household["owner_user_id"]),
                "created_at": str(household["created_at"]),
            },
            True,
        )

    def remove_member(self, *, household_id: str, user_id: str) -> bool:
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM household_members WHERE household_id = ? AND user_id = ?",
                (household_id, user_id),
            )
        return int(cur.rowcount) > 0
