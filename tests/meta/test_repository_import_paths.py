"""Tests for repository import paths."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_REPOSITORY_MODULE = REPO_ROOT / "src" / "dietary_guardian" / "services" / "repository.py"
LEGACY_API_AUTH_MODULE = REPO_ROOT / "apps" / "api" / "dietary_api" / "auth.py"
MIGRATED_CALLERS = [
    "src/dietary_guardian/infrastructure/persistence/sqlite_app_store.py",
    "tests/infrastructure/test_alerting_outbox.py",
    "tests/integration/test_integration_user_story_1.py",
    "tests/integration/test_integration_user_story_2.py",
    "tests/infrastructure/test_meal_record_persistence.py",
    "tests/infrastructure/test_medication_scheduler.py",
    "tests/application/test_notification_service.py",
    "tests/application/test_platform_tools.py",
    "tests/infrastructure/test_regressions_inference_and_alerting.py",
    "tests/application/test_trigger_alert.py",
    "tests/application/test_workflow_coordinator.py",
]
LEGACY_IMPORT = "from dietary_guardian.services.repository import SQLiteRepository"
CANONICAL_IMPORT = "from dietary_guardian.infrastructure.persistence import SQLiteRepository"
LEGACY_API_AUTH_IMPORT = "from apps.api.dietary_api.auth import build_user_profile_from_session"
CANONICAL_API_AUTH_IMPORT = "from dietary_guardian.application.auth.session_context import build_user_profile_from_session"


def test_infrastructure_persistence_exports_sqlite_repository() -> None:
    from dietary_guardian.infrastructure import persistence

    assert hasattr(persistence, "SQLiteRepository")


def test_legacy_repository_and_api_auth_modules_are_removed() -> None:
    assert not LEGACY_REPOSITORY_MODULE.exists()
    assert not LEGACY_API_AUTH_MODULE.exists()


def test_repo_local_callers_use_canonical_sqlite_repository_import() -> None:
    offenders: list[str] = []
    for relative_path in MIGRATED_CALLERS:
        contents = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        if LEGACY_IMPORT in contents:
            offenders.append(relative_path)
    assert offenders == []


def test_api_services_use_canonical_session_profile_helper_import() -> None:
    # Phase 2: business logic moved from services/ to application/; check both
    # the shim re-export files and the canonical application-layer destinations.
    paths_to_check = [
        # service shims that still contain the helper or re-export it
        "apps/api/dietary_api/services/reminders.py",
        # application-layer destinations (Phase 2 targets)
        "src/dietary_guardian/application/notifications/alert_session.py",
        "src/dietary_guardian/application/recommendations/suggestion_session.py",
        "src/dietary_guardian/application/meals/use_cases.py",
        "src/dietary_guardian/application/recommendations/use_cases.py",
        "src/dietary_guardian/application/notifications/reminder_materialization.py",
    ]
    offenders: list[str] = []
    for relative_path in paths_to_check:
        path = REPO_ROOT / relative_path
        if not path.exists():
            continue
        contents = path.read_text(encoding="utf-8")
        if LEGACY_API_AUTH_IMPORT in contents:
            offenders.append(relative_path)
    assert offenders == [], f"Files using legacy auth import: {offenders}"
