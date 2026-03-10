from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Callable, TypeVar

from dietary_guardian.application.emotion.ports import (
    EmotionInferencePort,
    SpeechEmotionInput,
    TextEmotionInput,
)
from dietary_guardian.models.emotion import EmotionInferenceResult

T = TypeVar("T")


class EmotionInferenceTimeoutError(RuntimeError):
    """Raised when inference exceeds configured wall-clock time."""


def _run_with_timeout(action: Callable[[], T], timeout_seconds: float) -> T:
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(action)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError as exc:
            raise EmotionInferenceTimeoutError("emotion inference timed out") from exc


def infer_text_emotion(
    *,
    port: EmotionInferencePort,
    payload: TextEmotionInput,
    timeout_seconds: float,
) -> EmotionInferenceResult:
    return _run_with_timeout(lambda: port.infer_text(payload), timeout_seconds)


def infer_speech_emotion(
    *,
    port: EmotionInferencePort,
    payload: SpeechEmotionInput,
    timeout_seconds: float,
) -> EmotionInferenceResult:
    return _run_with_timeout(lambda: port.infer_speech(payload), timeout_seconds)

