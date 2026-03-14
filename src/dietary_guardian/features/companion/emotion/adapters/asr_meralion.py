"""MERaLiON ASR adapter for emotion pipeline."""

from __future__ import annotations

import io
from typing import Any

import librosa
import numpy as np
import soundfile as sf
import torch

from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

from dietary_guardian.features.companion.emotion.ports import ASRPort
from dietary_guardian.platform.observability import get_logger

logger = get_logger(__name__)

_PROMPT_TEMPLATE = (
    "Instruction: {query} \n"
    "Follow the text instruction based on the following audio: <SpeechHere>"
)
_TRANSCRIBE_PROMPT = "Please transcribe this speech."


class MeralionASR(ASRPort):
    def __init__(self, repo_id: str) -> None:
        self._repo_id = repo_id
        self._device = "mps" if torch.backends.mps.is_available() else "cpu"
        self._torch_dtype = torch.float16 if torch.backends.mps.is_available() else torch.float32
        self._processor: Any = None
        self._model: Any = None

    def _ensure_loaded(self) -> None:
        if self._model is not None and self._processor is not None:
            return
        logger.info("emotion_asr_load_start repo_id=%s device=%s", self._repo_id, self._device)
        self._processor = AutoProcessor.from_pretrained(self._repo_id, trust_remote_code=True)
        self._model = AutoModelForSpeechSeq2Seq.from_pretrained(
            self._repo_id,
            torch_dtype=self._torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True,
            trust_remote_code=True,
        ).to(self._device)
        logger.info("emotion_asr_load_complete repo_id=%s", self._repo_id)

    def transcribe(
        self,
        audio_bytes: bytes,
        *,
        filename: str | None,
        language: str | None,
    ) -> str:
        del filename, language
        if not audio_bytes:
            raise ValueError("audio payload is empty")
        self._ensure_loaded()
        processor = self._processor
        model = self._model

        try:
            data, sample_rate = sf.read(io.BytesIO(audio_bytes))
        except Exception as exc:  # noqa: BLE001
            raise ValueError("failed to decode audio") from exc

        if isinstance(data, np.ndarray) and data.ndim > 1:
            data = np.mean(data, axis=1)
        audio_array = data.astype(np.float32)
        if sample_rate != 16000:
            audio_array = librosa.resample(y=audio_array, orig_sr=sample_rate, target_sr=16000)

        conversation = [
            [{"role": "user", "content": _PROMPT_TEMPLATE.format(query=_TRANSCRIBE_PROMPT)}]
        ]
        chat_prompt = processor.tokenizer.apply_chat_template(
            conversation=conversation,
            tokenize=False,
            add_generation_prompt=True,
        )

        inputs = processor(text=chat_prompt, audios=[audio_array], return_tensors="pt").to(self._device)
        inputs["input_features"] = inputs["input_features"].to(self._torch_dtype)

        generated_ids = model.generate(**inputs, max_new_tokens=256)
        transcript = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return transcript.strip()


__all__ = ["MeralionASR"]
