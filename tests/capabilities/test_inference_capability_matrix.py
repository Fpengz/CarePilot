"""Tests for inference capability matrix."""

from dietary_guardian.infrastructure.ai.engine import InferenceEngine
from dietary_guardian.infrastructure.ai.types import InferenceModality


def test_test_provider_capability_matrix_disables_image() -> None:
    engine = InferenceEngine(provider="test")

    profile = engine.capability_profile()

    assert profile.provider == "test"
    assert profile.supports[InferenceModality.TEXT] is True
    assert profile.supports[InferenceModality.IMAGE] is False
    assert engine.supports(InferenceModality.IMAGE) is False

