"""Application notifications package.

Provides use-case entry points for:

- ``alert_dispatch`` — reminder/alert delivery orchestration
- ``reminder_materialization`` — materialise scheduled notification rows and
  dispatch due items into the outbox
"""

from dietary_guardian.application.notifications.alert_dispatch import (
    DeliveryResult,
    dispatch_reminder,
    dispatch_reminder_async,
    send_in_app,
    send_push,
    trigger_alert,
)
from dietary_guardian.application.notifications.reminder_materialization import (
    cancel_reminder_notifications,
    dispatch_due_reminder_notifications,
    materialize_reminder_notifications,
    resolve_notification_preferences,
)

__all__ = [
    "DeliveryResult",
    "cancel_reminder_notifications",
    "dispatch_due_reminder_notifications",
    "dispatch_reminder",
    "dispatch_reminder_async",
    "materialize_reminder_notifications",
    "resolve_notification_preferences",
    "send_in_app",
    "send_push",
    "trigger_alert",
]
