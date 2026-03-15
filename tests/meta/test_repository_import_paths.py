"""Tests for repository import paths."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_DIRS = [
    REPO_ROOT / "src" / "care_pilot" / "application",
    REPO_ROOT / "src" / "care_pilot" / "domain",
    REPO_ROOT / "src" / "care_pilot" / "infrastructure",
    REPO_ROOT / "src" / "care_pilot" / "capabilities",
]
MIGRATED_CALLERS = [
    "src/care_pilot/platform/persistence/sqlite_app_store.py",
    "tests/infrastructure/test_alerting_outbox.py",
    "tests/infrastructure/test_meal_record_persistence.py",
    "tests/infrastructure/test_medication_scheduler.py",
    "tests/infrastructure/test_regressions_inference_and_alerting.py",
    "tests/infrastructure/test_reminder_scheduler.py",
    "tests/integration/test_integration_user_story_1.py",
    "tests/integration/test_integration_user_story_2.py",
]
LEGACY_IMPORT = "from care_pilot.infrastructure.persistence import SQLiteRepository"
CANONICAL_IMPORT = "from care_pilot.platform.persistence import SQLiteRepository"
LEGACY_API_AUTH_IMPORT = (
    "from care_pilot.application.auth.session_context import build_user_profile_from_session"
)
CANONICAL_API_AUTH_IMPORT = (
    "from care_pilot.platform.auth.session_context import build_user_profile_from_session"
)


def test_platform_persistence_exports_sqlite_repository() -> None:
    from care_pilot.platform import persistence

    assert hasattr(persistence, "SQLiteRepository")


def test_legacy_layers_are_removed() -> None:
    missing = [path for path in LEGACY_DIRS if path.exists()]
    assert missing == []


def test_repo_local_callers_use_canonical_sqlite_repository_import() -> None:
    offenders: list[str] = []
    for relative_path in MIGRATED_CALLERS:
        contents = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        if LEGACY_IMPORT in contents:
            offenders.append(relative_path)
    assert offenders == []


def test_api_services_use_canonical_session_profile_helper_import() -> None:
    paths_to_check = [
        "apps/api/carepilot_api/routes_shared.py",
        "apps/api/carepilot_api/routers/alerts.py",
        "apps/api/carepilot_api/routers/households.py",
        "apps/api/carepilot_api/routers/recommendations.py",
        "apps/api/carepilot_api/routers/reminders.py",
        "apps/api/carepilot_api/routers/suggestions.py",
        "apps/api/carepilot_api/routers/workflows.py",
        "src/care_pilot/features/reminders/notifications/alert_session.py",
        "src/care_pilot/features/recommendations/suggestion_session.py",
        "src/care_pilot/features/meals/api_service.py",
        "src/care_pilot/features/recommendations/use_cases.py",
        "src/care_pilot/features/reminders/notifications/reminder_materialization.py",
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
