"""
Persist message preferences in SQLite.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from care_pilot.features.reminders.domain.models import MessagePreference

from .base import SQLiteReminderRepositoryBase, parse_datetime


class ReminderPreferenceRepository(SQLiteReminderRepositoryBase):
    def replace_message_preferences(
        self,
        *,
        user_id: str,
        scope_type: str,
        scope_key: str | None,
        preferences: list[MessagePreference],
    ) -> list[MessagePreference]:
        with self._get_connection() as conn:
            conn.execute(
                """
                DELETE FROM message_preferences
                WHERE user_id = ? AND scope_type = ? AND (
                    (scope_key IS NULL AND ? IS NULL) OR scope_key = ?
                )
                """,
                (user_id, scope_type, scope_key, scope_key),
            )
            for preference in preferences:
                conn.execute(
                    """
                    INSERT INTO message_preferences
                    (id, user_id, scope_type, scope_key, channel, offset_minutes, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        preference.id,
                        preference.user_id,
                        preference.scope_type,
                        preference.scope_key,
                        preference.channel,
                        preference.offset_minutes,
                        int(preference.enabled),
                        preference.created_at.isoformat(),
                        preference.updated_at.isoformat(),
                    ),
                )
            conn.commit()
        return self.list_message_preferences(
            user_id=user_id, scope_type=scope_type, scope_key=scope_key
        )

    def list_message_preferences(
        self,
        *,
        user_id: str,
        scope_type: str | None = None,
        scope_key: str | None = None,
    ) -> list[MessagePreference]:
        query = (
            "SELECT id, user_id, scope_type, scope_key, channel, offset_minutes, enabled, created_at, updated_at "
            "FROM message_preferences WHERE user_id = ?"
        )
        params: list[Any] = [user_id]
        if scope_type is not None:
            query += " AND scope_type = ?"
            params.append(scope_type)
            if scope_key is None:
                query += " AND scope_key IS NULL"
            else:
                query += " AND scope_key = ?"
                params.append(scope_key)
        query += " ORDER BY scope_type, scope_key, offset_minutes, channel"
        with self._get_connection() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            MessagePreference(
                id=row[0],
                user_id=row[1],
                scope_type=row[2],
                scope_key=row[3],
                channel=row[4],
                offset_minutes=row[5],
                enabled=bool(row[6]),
                created_at=cast(datetime, parse_datetime(row[7])),
                updated_at=cast(datetime, parse_datetime(row[8])),
            )
            for row in rows
        ]
