"""Architecture tests for the feature-first namespace layout.

These tests lock in stable public namespaces that the repo can migrate toward
without breaking callers repeatedly during refactors.
"""


def test_agent_namespace_exports_core_capabilities() -> None:
    from dietary_guardian.agent import AgentRegistry, EmotionAgent

    assert AgentRegistry is not None
    assert EmotionAgent is not None


def test_platform_namespace_exports_persistence() -> None:
    from dietary_guardian.platform import persistence

    assert hasattr(persistence, "build_app_store")


def test_core_namespace_exports_time() -> None:
    from dietary_guardian.core import time

    assert hasattr(time, "resolve_timezone")
