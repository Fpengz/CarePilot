"""API helpers for reminder generation, listing, confirmation, and mobility settings.

Shim: business logic lives in
``dietary_guardian.application.notifications.reminders``.
"""

from __future__ import annotations

from dietary_guardian.application.auth.session_context import build_user_profile_from_session  # noqa: F401
from dietary_guardian.application.notifications.reminders import (  # noqa: F401
    confirm_reminder_for_session,
    generate_reminders_for_session,
    get_mobility_settings_for_session,
    list_reminders_for_session,
    update_mobility_settings_for_session,
)

__all__ = [
    "build_user_profile_from_session",
    "confirm_reminder_for_session",
    "generate_reminders_for_session",
    "get_mobility_settings_for_session",
    "list_reminders_for_session",
    "update_mobility_settings_for_session",
]
