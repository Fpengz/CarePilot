"""
Persist message endpoints in SQLite.
"""

from __future__ import annotations

from datetime import datetime
from typing import cast

from care_pilot.features.reminders.domain.models import MessageEndpoint

from .base import SQLiteReminderRepositoryBase, parse_datetime


class ReminderEndpointRepository(SQLiteReminderRepositoryBase):
    def replace_message_endpoints(
        self,
        *,
        user_id: str,
        endpoints: list[MessageEndpoint],
    ) -> list[MessageEndpoint]:
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM message_endpoints WHERE user_id = ?",
                (user_id,),
            )
            for endpoint in endpoints:
                conn.execute(
                    """
                    INSERT INTO message_endpoints
                    (id, user_id, channel, destination, verified, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        endpoint.id,
                        endpoint.user_id,
                        endpoint.channel,
                        endpoint.destination,
                        int(endpoint.verified),
                        endpoint.created_at.isoformat(),
                        endpoint.updated_at.isoformat(),
                    ),
                )
            conn.commit()
        return self.list_message_endpoints(user_id=user_id)

    def list_message_endpoints(self, *, user_id: str) -> list[MessageEndpoint]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, channel, destination, verified, created_at, updated_at
                FROM message_endpoints
                WHERE user_id = ?
                ORDER BY channel
                """,
                (user_id,),
            ).fetchall()
        return [
            MessageEndpoint(
                id=row[0],
                user_id=row[1],
                channel=row[2],
                destination=row[3],
                verified=bool(row[4]),
                created_at=cast(datetime, parse_datetime(row[5])),
                updated_at=cast(datetime, parse_datetime(row[6])),
            )
            for row in rows
        ]

    def get_reminder_notification_endpoint(
        self,
        *,
        user_id: str,
        channel: str,
    ) -> MessageEndpoint | None:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, user_id, channel, destination, verified, created_at, updated_at
                FROM message_endpoints
                WHERE user_id = ? AND channel = ?
                """,
                (user_id, channel),
            ).fetchone()
        if row is None:
            return None
        return MessageEndpoint(
            id=row[0],
            user_id=row[1],
            channel=row[2],
            destination=row[3],
            verified=bool(row[4]),
            created_at=cast(datetime, parse_datetime(row[5])),
            updated_at=cast(datetime, parse_datetime(row[6])),
        )

    def get_message_endpoint_by_destination(
        self,
        *,
        channel: str,
        destination: str,
    ) -> MessageEndpoint | None:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, user_id, channel, destination, verified, created_at, updated_at
                FROM message_endpoints
                WHERE channel = ? AND destination = ?
                """,
                (channel, destination),
            ).fetchone()
        if row is None:
            return None
        return MessageEndpoint(
            id=row[0],
            user_id=row[1],
            channel=row[2],
            destination=row[3],
            verified=bool(row[4]),
            created_at=cast(datetime, parse_datetime(row[5])),
            updated_at=cast(datetime, parse_datetime(row[6])),
        )
