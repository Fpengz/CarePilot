from dietary_guardian.models.inference import InferenceModality
from dietary_guardian.services.inference_engine import InferenceEngine


def test_test_provider_capability_matrix_disables_image() -> None:
    engine = InferenceEngine(provider="test")

    profile = engine.capability_profile()

    assert profile.provider == "test"
    assert profile.supports[InferenceModality.TEXT] is True
    assert profile.supports[InferenceModality.IMAGE] is False
    assert engine.supports(InferenceModality.IMAGE) is False

