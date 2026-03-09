from typing import get_args, get_type_hints

from dietary_guardian.infrastructure import persistence
from dietary_guardian.services.alerting_service import AlertRepositoryProtocol
from dietary_guardian.services.platform_tools import build_platform_tool_registry
from dietary_guardian.services.reminder_scheduler import run_reminder_scheduler_once


def test_persistence_exports_backend_neutral_builder_and_contracts() -> None:
    assert hasattr(persistence, "build_app_store")
    assert hasattr(persistence, "AppStoreBackend")
    assert hasattr(persistence, "ReminderSchedulerRepository")


def test_platform_tool_registry_accepts_alert_repository_protocol() -> None:
    assert get_type_hints(build_platform_tool_registry)["repository"] is AlertRepositoryProtocol


def test_reminder_scheduler_depends_on_backend_neutral_repository_contract() -> None:
    repository_hint = get_type_hints(run_reminder_scheduler_once)["repository"]
    hint_args = get_args(repository_hint)
    assert any(getattr(item, "__name__", "") == "ReminderSchedulerRepository" for item in hint_args)
