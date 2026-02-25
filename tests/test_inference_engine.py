from dietary_guardian.models.inference import InferenceModality
from dietary_guardian.config.settings import get_settings
from dietary_guardian.services.inference_engine import InferenceEngine


def test_inference_engine_strategy_selection_test_provider(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "test")
    engine = InferenceEngine()
    assert engine.health().provider == "test"
    assert engine.supports(InferenceModality.TEXT) is True
    assert engine.supports(InferenceModality.IMAGE) is False
    get_settings.cache_clear()


def test_inference_engine_strategy_selection_local_provider(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
    engine = InferenceEngine()
    assert engine.health().provider == "ollama"
    assert engine.supports(InferenceModality.IMAGE) is True
    get_settings.cache_clear()
