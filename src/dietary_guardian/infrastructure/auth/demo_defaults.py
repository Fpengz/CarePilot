"""Infrastructure support for demo defaults."""

from __future__ import annotations

from dietary_guardian.config.app import AppSettings as Settings
from dietary_guardian.domain.identity.models import AccountRole, ProfileMode

DemoUserSeed = tuple[str, str, str, AccountRole, ProfileMode, str]


def build_demo_user_seeds(settings: Settings) -> list[DemoUserSeed]:
    return [
        (
            "user_001",
            "member@example.com",
            "Alex Member",
            "member",
            "self",
            settings.auth.demo_member_password,
        ),
        (
            "care_001",
            "helper@example.com",
            "Casey Helper",
            "member",
            "caregiver",
            settings.auth.demo_helper_password,
        ),
        (
            "ops_001",
            "admin@example.com",
            "Ops Admin",
            "admin",
            "self",
            settings.auth.demo_admin_password,
        ),
    ]
