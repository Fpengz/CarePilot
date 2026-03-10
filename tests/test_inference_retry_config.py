from pydantic import BaseModel

from dietary_guardian.agents.executor import InferenceEngine
from dietary_guardian.config.settings import get_settings
from dietary_guardian.models.inference import InferenceModality, InferenceRequest


class _DummyOutput(BaseModel):
    value: str = "ok"


def test_local_provider_defaults_output_validation_retries_to_zero(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
    settings = get_settings()
    assert settings.llm.local_output_validation_retries == 0
    get_settings.cache_clear()


def test_inference_engine_logs_retry_exhaustion_with_estimated_request_count(monkeypatch, caplog) -> None:
    class FakeResult:
        output = _DummyOutput()

    class FakeAgent:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            self.kwargs = kwargs

        async def run(self, prompt: str):  # noqa: ANN201
            del prompt
            raise RuntimeError("Exceeded maximum retries (1) for output validation")

    monkeypatch.setattr("dietary_guardian.agents.executor.Agent", FakeAgent)
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LOCAL_OUTPUT_VALIDATION_RETRIES", "0")
    get_settings.cache_clear()

    engine = InferenceEngine(provider="test")
    engine.provider = "ollama"
    engine.strategy.provider_name = "ollama"

    request = InferenceRequest(
        request_id="req1",
        modality=InferenceModality.TEXT,
        payload={"prompt": "hello"},
        output_schema=_DummyOutput,
        system_prompt="sys",
    )

    import asyncio
    import logging

    caplog.set_level(logging.INFO)
    try:
        asyncio.run(engine.infer(request))
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected RuntimeError")

    assert "inference_output_validation_retry_exhausted" in caplog.text
    assert "estimated_model_requests=1" in caplog.text
    get_settings.cache_clear()

