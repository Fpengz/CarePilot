"""Tests for inference engine."""

import asyncio

import pytest
from pydantic import BaseModel

from care_pilot.agent.runtime.inference_engine import InferenceEngine
from care_pilot.config.app import get_settings
from care_pilot.agent.runtime.inference_types import (
    InferenceModality,
    InferenceRequest,
)
from pydantic_ai.messages import PartEndEvent, TextPart


def test_inference_engine_strategy_selection_test_provider(
    monkeypatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "test")
    engine = InferenceEngine()
    assert engine.health().provider == "test"
    assert engine.supports(InferenceModality.TEXT) is True
    assert engine.supports(InferenceModality.IMAGE) is False
    get_settings.cache_clear()


def test_inference_engine_strategy_selection_local_provider(
    monkeypatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
    engine = InferenceEngine()
    assert engine.health().provider == "ollama"
    assert engine.supports(InferenceModality.IMAGE) is True
    get_settings.cache_clear()


class _TestOutput(BaseModel):
    message: str


class _RecoveryOutput(BaseModel):
    value: int


class _ListRecoveryOutput(BaseModel):
    instructions: list[dict[str, int]]
    confidence_score: float = 0.0
    warnings: list[str] = []


def test_inference_engine_recovers_json_on_validation_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "test")

    class _FakeAgent:
        def __init__(
            self, model, output_type, system_prompt, output_retries
        ):  # noqa: ANN001, ARG002
            self.output_type = output_type

        async def run(self, prompt, event_stream_handler=None):  # noqa: ANN001
            async def _events():
                yield PartEndEvent(
                    index=0, part=TextPart(content='{"value": 42}')
                )

            if event_stream_handler is not None:
                await event_stream_handler(None, _events())
            raise ValueError("Output validation failed")

    monkeypatch.setattr(
        "care_pilot.agent.runtime.inference_engine.Agent",
        _FakeAgent,
    )

    engine = InferenceEngine()
    request = InferenceRequest(
        request_id="recovery-case",
        user_id="user_001",
        modality=InferenceModality.TEXT,
        payload={"prompt": "test"},
        output_schema=_RecoveryOutput,
        system_prompt="test",
    )

    response = asyncio.run(engine.infer(request))
    assert response.structured_output.value == 42
    assert response.warnings
    get_settings.cache_clear()


def test_inference_engine_recovers_list_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "test")

    class _FakeAgent:
        def __init__(
            self, model, output_type, system_prompt, output_retries
        ):  # noqa: ANN001, ARG002
            self.output_type = output_type

        async def run(self, prompt, event_stream_handler=None):  # noqa: ANN001
            async def _events():
                yield PartEndEvent(
                    index=0,
                    part=TextPart(content='```json\n[{"dose": 1}]\n```'),
                )

            if event_stream_handler is not None:
                await event_stream_handler(None, _events())
            raise ValueError("Output validation failed")

    monkeypatch.setattr(
        "care_pilot.agent.runtime.inference_engine.Agent",
        _FakeAgent,
    )

    engine = InferenceEngine()
    request = InferenceRequest(
        request_id="recovery-list",
        user_id="user_002",
        modality=InferenceModality.TEXT,
        payload={"prompt": "test"},
        output_schema=_ListRecoveryOutput,
        system_prompt="test",
    )

    response = asyncio.run(engine.infer(request))
    assert response.structured_output.instructions == [{"dose": 1}]
    assert response.structured_output.warnings
    get_settings.cache_clear()


def test_inference_engine_enforces_wall_clock_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
