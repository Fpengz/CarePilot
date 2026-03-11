"""API orchestration for reminder notification preferences, endpoints, and logs.

Shim: business logic lives in
``dietary_guardian.application.notifications.reminder_materialization``.
"""

from __future__ import annotations

from dietary_guardian.application.notifications.reminder_materialization import (  # noqa: F401
    list_notification_endpoints,
    list_notification_preferences,
    list_reminder_notification_logs,
    list_reminder_notification_schedules,
    replace_notification_endpoints,
    replace_notification_preferences,
)

__all__ = [
    "list_notification_endpoints",
    "list_notification_preferences",
    "list_reminder_notification_logs",
    "list_reminder_notification_schedules",
    "replace_notification_endpoints",
    "replace_notification_preferences",
]
