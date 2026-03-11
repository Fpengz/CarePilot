"""API helpers for workflow-derived notification feeds and read state.

Shim: business logic lives in
``dietary_guardian.application.notifications.use_cases``.
"""

from __future__ import annotations

from dietary_guardian.application.notifications.use_cases import (  # noqa: F401
    NotificationReadStateStore,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)

__all__ = [
    "NotificationReadStateStore",
    "list_notifications",
    "mark_all_notifications_read",
    "mark_notification_read",
]
