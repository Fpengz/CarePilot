"""Tests for the feature-first backend architecture layout."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_feature_first_backend_packages_exist() -> None:
    required_paths = [
        "src/care_pilot/core/__init__.py",
        "src/care_pilot/core/config/__init__.py",
        "src/care_pilot/core/errors.py",
        "src/care_pilot/core/events.py",
        "src/care_pilot/core/ids.py",
        "src/care_pilot/core/time/__init__.py",
        "src/care_pilot/core/types.py",
        "src/care_pilot/features/__init__.py",
        "src/care_pilot/features/companion/__init__.py",
        "src/care_pilot/features/companion/core/__init__.py",
        "src/care_pilot/features/companion/personalization/__init__.py",
        "src/care_pilot/features/companion/engagement/__init__.py",
        "src/care_pilot/features/companion/care_plans/__init__.py",
        "src/care_pilot/features/companion/interactions/__init__.py",
        "src/care_pilot/features/companion/clinician_digest/__init__.py",
        "src/care_pilot/features/companion/impact/__init__.py",
        "src/care_pilot/features/meals/service.py",
        "src/care_pilot/features/recommendations/service.py",
        "src/care_pilot/features/reminders/service.py",
        "src/care_pilot/features/reports/service.py",
        "src/care_pilot/features/safety/service.py",
        "src/care_pilot/agent/__init__.py",
        "src/care_pilot/agent/core/__init__.py",
        "src/care_pilot/agent/runtime/__init__.py",
        "src/care_pilot/agent/meal_analysis/__init__.py",
        "src/care_pilot/agent/recommendation/__init__.py",
        "src/care_pilot/agent/emotion/__init__.py",
        "src/care_pilot/agent/chat/__init__.py",
        "src/care_pilot/platform/__init__.py",
        "src/care_pilot/platform/auth/__init__.py",
        "src/care_pilot/platform/cache/__init__.py",
        "src/care_pilot/platform/messaging/__init__.py",
        "src/care_pilot/platform/observability/__init__.py",
        "src/care_pilot/platform/persistence/__init__.py",
        "src/care_pilot/platform/scheduling/__init__.py",
        "src/care_pilot/platform/storage/__init__.py",
    ]
    missing = [path for path in required_paths if not (ROOT / path).exists()]
    assert missing == []


def test_api_service_shims_delegate_to_feature_services() -> None:
    expected_imports = {
        "apps/api/carepilot_api/services/companion.py": (
            "from care_pilot.features.companion.core.use_cases import"
        ),
        "apps/api/carepilot_api/services/companion_context.py": (
            "from care_pilot.features.companion.core.use_cases import"
        ),
        "apps/api/carepilot_api/services/meals.py": "from care_pilot.features.meals.service import",
        "apps/api/carepilot_api/services/recommendations.py": (
            "from care_pilot.features.recommendations.service import"
        ),
        "apps/api/carepilot_api/services/reminders.py": (
            "from care_pilot.features.reminders.service import"
        ),
    }
    offenders: list[str] = []
    for relative_path, expected_import in expected_imports.items():
        contents = (ROOT / relative_path).read_text(encoding="utf-8")
        if expected_import not in contents:
            offenders.append(relative_path)
    assert offenders == []


def test_runtime_entrypoints_use_agent_and_platform_packages() -> None:
    expectations = {
        "apps/api/carepilot_api/deps.py": [
            "from care_pilot.agent",
            "from care_pilot.platform",
        ],
        "apps/workers/run.py": [
            "from care_pilot.platform",
        ],
    }
    offenders: list[str] = []
    for relative_path, expected_fragments in expectations.items():
        contents = (ROOT / relative_path).read_text(encoding="utf-8")
        if any(fragment not in contents for fragment in expected_fragments):
            offenders.append(relative_path)
    assert offenders == []
