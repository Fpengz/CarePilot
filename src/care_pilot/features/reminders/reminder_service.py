"""
Provide the reminders service entrypoint.

This module exposes the main reminder workflows to callers.
"""

from care_pilot.features.reminders.notifications.reminder_materialization import (
    list_message_endpoints,
    list_message_logs,
    list_message_preferences,
    list_message_schedules,
    replace_message_endpoints,
    replace_message_preferences,
)
from care_pilot.features.reminders.notifications.reminders import (
    confirm_reminder_for_session,
    generate_reminders_for_session,
    get_mobility_settings_for_session,
    list_reminders_for_session,
    update_mobility_settings_for_session,
)
from care_pilot.features.reminders.use_cases import (
    apply_occurrence_action_for_session,
    create_reminder_definition_for_user,
    list_history_occurrences_for_user,
    list_reminder_definitions_for_user,
    list_upcoming_occurrences_for_user,
    update_reminder_definition_for_user,
)
from care_pilot.features.reminders.use_cases.inbound_messages import handle_inbound_message

__all__ = [
    "apply_occurrence_action_for_session",
    "confirm_reminder_for_session",
    "create_reminder_definition_for_user",
    "generate_reminders_for_session",
    "get_mobility_settings_for_session",
    "handle_inbound_message",
    "list_history_occurrences_for_user",
    "list_message_endpoints",
    "list_message_logs",
    "list_message_preferences",
    "list_message_schedules",
    "list_reminder_definitions_for_user",
    "list_reminders_for_session",
    "list_upcoming_occurrences_for_user",
    "replace_message_endpoints",
    "replace_message_preferences",
    "update_mobility_settings_for_session",
    "update_reminder_definition_for_user",
]
