import asyncio

import pytest
from pydantic import BaseModel

from dietary_guardian.models.inference import InferenceModality
from dietary_guardian.models.inference import InferenceRequest
from dietary_guardian.config.settings import get_settings
from dietary_guardian.agents.executor import InferenceEngine


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


class _TestOutput(BaseModel):
    message: str


def test_inference_engine_enforces_wall_clock_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "test")
    monkeypatch.setenv("LLM_INFERENCE_WALL_CLOCK_TIMEOUT_SECONDS", "0.1")
    engine = InferenceEngine()

    async def _slow_run(request: InferenceRequest):  # noqa: ARG001
        await asyncio.sleep(0.2)
        return None

    monkeypatch.setattr(engine.strategy, "run", _slow_run)
    request = InferenceRequest(
        request_id="timeout-case",
        user_id="user_001",
        modality=InferenceModality.TEXT,
        payload={"prompt": "test"},
        output_schema=_TestOutput,
        system_prompt="test",
    )

    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(engine.infer(request))
    get_settings.cache_clear()
