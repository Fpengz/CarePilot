"""Tests for the feature-first backend architecture layout."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_feature_first_backend_packages_exist() -> None:
    required_paths = [
        "src/dietary_guardian/core/__init__.py",
        "src/dietary_guardian/core/config/__init__.py",
        "src/dietary_guardian/core/errors.py",
        "src/dietary_guardian/core/events.py",
        "src/dietary_guardian/core/ids.py",
        "src/dietary_guardian/core/time/__init__.py",
        "src/dietary_guardian/core/types.py",
        "src/dietary_guardian/features/__init__.py",
        "src/dietary_guardian/features/companion/__init__.py",
        "src/dietary_guardian/features/companion/core/service.py",
        "src/dietary_guardian/features/companion/personalization/service.py",
        "src/dietary_guardian/features/companion/engagement/service.py",
        "src/dietary_guardian/features/companion/care_plans/service.py",
        "src/dietary_guardian/features/companion/interactions/service.py",
        "src/dietary_guardian/features/companion/clinician_digest/service.py",
        "src/dietary_guardian/features/companion/impact/service.py",
        "src/dietary_guardian/features/meals/service.py",
        "src/dietary_guardian/features/recommendations/service.py",
        "src/dietary_guardian/features/reminders/service.py",
        "src/dietary_guardian/features/reports/service.py",
        "src/dietary_guardian/features/safety/service.py",
        "src/dietary_guardian/agent/__init__.py",
        "src/dietary_guardian/agent/shared/__init__.py",
        "src/dietary_guardian/agent/meal_analysis/__init__.py",
        "src/dietary_guardian/agent/recommendation/__init__.py",
        "src/dietary_guardian/agent/emotion/__init__.py",
        "src/dietary_guardian/agent/vision/__init__.py",
        "src/dietary_guardian/platform/__init__.py",
        "src/dietary_guardian/platform/auth/__init__.py",
        "src/dietary_guardian/platform/cache/__init__.py",
        "src/dietary_guardian/platform/messaging/__init__.py",
        "src/dietary_guardian/platform/observability/__init__.py",
        "src/dietary_guardian/platform/persistence/__init__.py",
        "src/dietary_guardian/platform/scheduling/__init__.py",
        "src/dietary_guardian/platform/storage/__init__.py",
    ]
    missing = [path for path in required_paths if not (ROOT / path).exists()]
    assert missing == []


def test_api_service_shims_delegate_to_feature_services() -> None:
    expected_imports = {
        "apps/api/dietary_api/services/companion.py": (
            "from dietary_guardian.features.companion.core.service import"
        ),
        "apps/api/dietary_api/services/companion_context.py": (
            "from dietary_guardian.features.companion.core.service import"
        ),
        "apps/api/dietary_api/services/meals.py": "from dietary_guardian.features.meals.service import",
        "apps/api/dietary_api/services/recommendations.py": (
            "from dietary_guardian.features.recommendations.service import"
        ),
        "apps/api/dietary_api/services/reminders.py": (
            "from dietary_guardian.features.reminders.service import"
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
        "apps/api/dietary_api/deps.py": [
            "from dietary_guardian.agent",
            "from dietary_guardian.platform",
        ],
        "apps/workers/run.py": [
            "from dietary_guardian.platform",
        ],
    }
    offenders: list[str] = []
    for relative_path, expected_fragments in expectations.items():
        contents = (ROOT / relative_path).read_text(encoding="utf-8")
        if any(fragment not in contents for fragment in expected_fragments):
            offenders.append(relative_path)
    assert offenders == []
