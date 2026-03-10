"""Runtime contract regressions for infrastructure and scheduler imports."""

import subprocess
import sys
from pathlib import Path
from typing import get_args, get_type_hints

from dietary_guardian.infrastructure import persistence
from dietary_guardian.application.contracts.notifications import AlertRepositoryProtocol
from dietary_guardian.application.tooling.platform_registry import build_platform_tool_registry
from dietary_guardian.infrastructure.schedulers.reminder_scheduler import run_reminder_scheduler_once

REPO_ROOT = Path(__file__).resolve().parents[1]


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


def test_alert_models_and_reminder_scheduler_import_without_circular_dependency() -> None:
    command = [
        sys.executable,
        "-c",
        "import dietary_guardian.domain.alerts.models; import dietary_guardian.infrastructure.schedulers.reminder_scheduler",
    ]
    result = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
