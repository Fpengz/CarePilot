from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from dietary_guardian.infrastructure.persistence.postgres_schema import ensure_postgres_household_schema


def _load_psycopg_module() -> Any:
    try:
        import psycopg
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError(
            "psycopg package is required for HOUSEHOLD_STORE_BACKEND=postgres. Run `uv sync` after updating dependencies."
        ) from exc
    return psycopg


class PostgresHouseholdStore:
    def __init__(self, *, dsn: str) -> None:
        self._psycopg = _load_psycopg_module()
        self._dsn = dsn
        with self._connect() as conn:
            ensure_postgres_household_schema(conn)

    def _connect(self) -> Any:
        return self._psycopg.connect(self._dsn, autocommit=True)

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def get_household_for_user(self, user_id: str) -> dict[str, Any] | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT h.household_id, h.name, h.owner_user_id, h.created_at
                FROM household_members m
                JOIN households h ON h.household_id = m.household_id
                WHERE m.user_id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return {
            "household_id": str(row[0]),
            "name": str(row[1]),
            "owner_user_id": str(row[2]),
            "created_at": row[3].isoformat(),
        }

    def get_household_by_id(self, household_id: str) -> dict[str, Any] | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT household_id, name, owner_user_id, created_at FROM households WHERE household_id = %s",
                (household_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return {
            "household_id": str(row[0]),
            "name": str(row[1]),
            "owner_user_id": str(row[2]),
            "created_at": row[3].isoformat(),
        }

    def create_household(self, *, owner_user_id: str, owner_display_name: str, name: str) -> dict[str, Any]:
        now = self._now()
        household_id = f"hh_{uuid4().hex[:12]}"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO households (household_id, name, owner_user_id, created_at) VALUES (%s, %s, %s, %s)",
                (household_id, name, owner_user_id, now),
            )
            cur.execute(
                """
                INSERT INTO household_members (household_id, user_id, display_name, role, joined_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (household_id, owner_user_id, owner_display_name, "owner", now),
            )
        return {
            "household_id": household_id,
            "name": name,
            "owner_user_id": owner_user_id,
            "created_at": now.isoformat(),
        }

    def list_members(self, household_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, display_name, role, joined_at
                FROM household_members
                WHERE household_id = %s
                ORDER BY CASE role WHEN 'owner' THEN 0 ELSE 1 END, joined_at ASC
                """,
                (household_id,),
            )
            rows = cur.fetchall()
        return [
            {
                "user_id": str(row[0]),
                "display_name": str(row[1]),
                "role": str(row[2]),
                "joined_at": row[3].isoformat(),
            }
            for row in rows
        ]

    def get_member_role(self, household_id: str, user_id: str) -> str | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT role FROM household_members WHERE household_id = %s AND user_id = %s",
                (household_id, user_id),
            )
            row = cur.fetchone()
        return None if row is None else str(row[0])

    def rename_household(self, *, household_id: str, name: str) -> dict[str, Any] | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE households SET name = %s WHERE household_id = %s",
                (name, household_id),
            )
            if cur.rowcount == 0:
                return None
        return self.get_household_by_id(household_id)

    def create_invite(self, *, household_id: str, created_by_user_id: str) -> dict[str, Any]:
        now = self._now()
        invite_id = f"inv_{uuid4().hex[:12]}"
        code = f"hh_{secrets.token_urlsafe(6).rstrip('=')}"
        expires_at = now + timedelta(days=7)
        max_uses = 10
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO household_invites (
                    invite_id, household_id, code, created_by_user_id, created_at, expires_at, max_uses, uses, revoked_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 0, NULL)
                """,
                (invite_id, household_id, code, created_by_user_id, now, expires_at, max_uses),
            )
        return {
            "invite_id": invite_id,
            "household_id": household_id,
            "code": code,
            "created_by_user_id": created_by_user_id,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "max_uses": max_uses,
            "uses": 0,
        }

    def join_by_invite(self, *, code: str, user_id: str, display_name: str) -> tuple[dict[str, Any], bool] | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT invite_id, household_id, expires_at, max_uses, uses, revoked_at
                FROM household_invites
                WHERE code = %s
                """,
                (code,),
            )
            invite = cur.fetchone()
        if invite is None or invite[5] is not None:
            return None
        expires_at = invite[2]
        if self._now() >= expires_at.astimezone(timezone.utc):
            return None

        household_id = str(invite[1])
        existing = self.get_household_for_user(user_id)
        if existing is not None:
            return (existing, False)

        uses = int(invite[4])
        max_uses = int(invite[3])
        if uses >= max_uses:
            return None

        now = self._now()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO household_members (household_id, user_id, display_name, role, joined_at)
                VALUES (%s, %s, %s, 'member', %s)
                """,
                (household_id, user_id, display_name, now),
            )
            cur.execute(
                "UPDATE household_invites SET uses = uses + 1 WHERE invite_id = %s",
                (str(invite[0]),),
            )
        household = self.get_household_by_id(household_id)
        if household is None:
            return None
        return (household, True)

    def remove_member(self, *, household_id: str, user_id: str) -> bool:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM household_members WHERE household_id = %s AND user_id = %s",
                (household_id, user_id),
            )
            return cur.rowcount > 0

    def close(self) -> None:
        return None
