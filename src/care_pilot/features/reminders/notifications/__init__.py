"""Application notifications package.

Provides use-case entry points for:

- ``alert_dispatch`` — reminder/alert delivery orchestration
- ``reminder_materialization`` — materialise scheduled notification rows and
  dispatch due items into the outbox
"""

from care_pilot.features.reminders.notifications.alert_dispatch import (
    DeliveryResult,
    dispatch_reminder,
    dispatch_reminder_async,
    send_in_app,
    send_push,
    trigger_alert,
)
from care_pilot.features.reminders.notifications.reminder_materialization import (
    cancel_reminder_notifications,
    dispatch_due_reminder_notifications,
    materialize_reminder_notifications,
    resolve_message_preferences,
)

__all__ = [
    "DeliveryResult",
    "cancel_reminder_notifications",
    "dispatch_due_reminder_notifications",
    "dispatch_reminder",
    "dispatch_reminder_async",
    "materialize_reminder_notifications",
    "resolve_message_preferences",
    "send_in_app",
    "send_push",
    "trigger_alert",
]
