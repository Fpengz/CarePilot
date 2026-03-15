"""Whisper ASR adapter for emotion pipeline."""

from __future__ import annotations

import io
import re
from typing import Any

import numpy as np
import soundfile as sf
from transformers import pipeline

from care_pilot.features.companion.emotion.ports import ASRPort
from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)


def _safe_preview(text: str, *, limit: int = 160) -> str:
    preview = text[:limit].replace("\n", " ")
    preview = re.sub(r"[0-9]", "x", preview)
    preview = re.sub(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "[redacted-email]", preview
    )
    return preview


class WhisperASR(ASRPort):
    def __init__(self, repo_id: str, device: str) -> None:
        self._repo_id = repo_id
        self._device = 0 if device == "cuda" else -1
        self._pipeline: Any = None

    def _ensure_loaded(self) -> None:
        if self._pipeline is not None:
            return
        logger.info(
            "emotion_asr_load_start repo_id=%s device=%s",
            self._repo_id,
            self._device,
        )
        self._pipeline = pipeline(
            "automatic-speech-recognition",
            model=self._repo_id,
            device=self._device,
        )
        logger.info("emotion_asr_load_complete repo_id=%s", self._repo_id)

    def transcribe(
        self,
        audio_bytes: bytes,
        *,
        filename: str | None,
        language: str | None,
    ) -> str:
        logger.info(
            "emotion_asr_request repo_id=%s bytes=%s filename=%s language=%s",
            self._repo_id,
            len(audio_bytes),
            filename or "none",
            language or "auto",
        )
        if not audio_bytes:
            raise ValueError("audio payload is empty")
        self._ensure_loaded()

        try:
            data, sample_rate = sf.read(io.BytesIO(audio_bytes))
        except Exception as exc:
            raise ValueError("failed to decode audio") from exc

        if isinstance(data, np.ndarray) and data.ndim > 1:
            data = np.mean(data, axis=1)
        audio_array = data.astype(np.float32)

        # Whisper pipeline handles resampling if sampling_rate is provided to __call__
        # or it uses the model's expected rate.
        result = self._pipeline(
            audio_array,
            generate_kwargs={"language": language} if language else None,
        )
        text = result["text"].strip()
        logger.info(
            "emotion_asr_response repo_id=%s text_len=%s preview=%s",
            self._repo_id,
            len(text),
            _safe_preview(text),
        )
        return text


__all__ = ["WhisperASR"]
