"""
Transcribe audio inputs for the chat agent.

This module provides audio transcription helpers backed by Groq Whisper
or a local MERaLiON model for Singapore-English speech.

Example:
    agent = AudioAgent()
    text = await agent.transcribe_bytes(raw_bytes)
"""

import asyncio
import base64
import io
import mimetypes
from typing import Any, cast

import httpx
import librosa
import numpy as np
import soundfile as sf
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

from care_pilot.platform.observability import get_logger
from care_pilot.platform.runtime.executors import get_io_executor, get_ml_executor
from care_pilot.platform.runtime.hf_loader import get_hf_loader

_PROMPT_TEMPLATE = (
    "Instruction: {query} \nFollow the text instruction based on the following audio: <SpeechHere>"
)
_TRANSCRIBE_PROMPT = "Please transcribe this speech."

logger = get_logger(__name__)


class AudioAgent:
    """Agent that transcribes audio to text using OpenAI-compatible ASR or MERaLiON."""

    def __init__(
        self,
        *,
        repo_id: str | None = None,
        groq_api_key: str | None = None,
        provider: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        model_id: str | None = None,
        model_cache_dir: str | None = None,
        remote_inference_url: str | None = None,
    ) -> None:
        self.repo_id = repo_id or "MERaLiON/MERaLiON-2-3B"
        self._groq_api_key = groq_api_key
        self._provider = (provider or "").strip().lower()
        self._api_key = api_key
        self._base_url = base_url
        self._model_id = model_id
        self.model_cache_dir = model_cache_dir
        self._remote_inference_url = remote_inference_url
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.torch_dtype = torch.float16 if torch.backends.mps.is_available() else torch.float32
        self.processor = None
        self.model = None
        self._async_client = httpx.AsyncClient(timeout=60.0)

    # ------------------------------------------------------------------
    # MERaLiON (local or remote)
    # ------------------------------------------------------------------

    def load_model(self) -> None:
        """Download & load the MERaLiON model onto the local device."""
        if self._provider == "remote":
            return  # No local load needed

        logger.info(
            "audio_agent_load_start repo_id=%s device=%s",
            self.repo_id,
            self.device,
        )
        self.processor = get_hf_loader(
            self.repo_id,
            load_func=cast(Any, AutoProcessor.from_pretrained),
            cache_dir=self.model_cache_dir,
            trust_remote_code=True,
        )
        self.model = get_hf_loader(
            self.repo_id,
            load_func=cast(Any, AutoModelForSpeechSeq2Seq.from_pretrained),
            cache_dir=self.model_cache_dir,
            torch_dtype=self.torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True,
            trust_remote_code=True,
        ).to(self.device)
        logger.info("audio_agent_load_complete repo_id=%s", self.repo_id)

    async def transcribe(self, audio_input: tuple) -> str:
        """Transcribe audio using MERaLiON (local or remote)."""
        if self._provider == "remote":
            return await self._transcribe_remote(audio_input)

        if self.model is None or self.processor is None:
            return "[MERaLiON] Model not loaded — call load_model() first."

        if audio_input is None:
            return "Error: No audio provided."

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(get_ml_executor(), self._transcribe_sync, audio_input)

    async def _transcribe_remote(self, audio_input: tuple) -> str:
        if not self._remote_inference_url:
            raise ValueError("remote_inference_url must be provided for provider=remote")

        sample_rate, audio_array = audio_input
        # Convert to WAV bytes for transmission
        buffer = io.BytesIO()
        sf.write(buffer, audio_array, sample_rate, format="WAV")
        buffer.seek(0)

        files = {"audio": ("audio.wav", buffer, "audio/wav")}
        data = {"context_features": "{}"}  # Required by current remote implementation

        response = await self._async_client.post(
            f"{self._remote_inference_url}/infer/speech", files=files, data=data
        )
        response.raise_for_status()
        result = response.json()
        # MERaLiON implementation returns transcription in a specific field if it's an emotion pipeline
        # but here we just need the text.
        return result.get("transcription") or result.get("text") or ""

    def _transcribe_sync(self, audio_input: tuple) -> str:
        sample_rate, audio_array = audio_input
        if sample_rate != 16000:
            audio_array = librosa.resample(
                y=audio_array.astype(np.float32),
                orig_sr=sample_rate,
                target_sr=16000,
            )

        # Local providers must have models loaded
        assert self.processor is not None
        assert self.model is not None

        conversation = [
            [
                {
                    "role": "user",
                    "content": _PROMPT_TEMPLATE.format(query=_TRANSCRIBE_PROMPT),
                }
            ]
        ]
        chat_prompt = self.processor.tokenizer.apply_chat_template(
            conversation=conversation,
            tokenize=False,
            add_generation_prompt=True,
        )

        inputs = self.processor(text=chat_prompt, audios=[audio_array], return_tensors="pt").to(
            self.device
        )
        inputs["input_features"] = inputs["input_features"].to(self.torch_dtype)

        generated_ids = self.model.generate(**inputs, max_new_tokens=256)
        return self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

    # ------------------------------------------------------------------
    # Cloud ASR (Groq / OpenAI)
    # ------------------------------------------------------------------

    async def transcribe_bytes(self, raw_bytes: bytes, filename: str = "audio.webm") -> str:
        """Transcribe raw audio bytes (webm/mp3/wav/ogg) via cloud ASR."""
        provider = self._provider
        loop = asyncio.get_running_loop()

        if provider in {"groq"}:
            return await loop.run_in_executor(
                get_io_executor(), self._transcribe_groq, raw_bytes, filename
            )
        if provider in {"qwen", "openai", "openai-compatible", "compatible"}:
            return await loop.run_in_executor(
                get_io_executor(), self._transcribe_openai_compatible, raw_bytes, filename
            )
        if provider == "remote":
            # Delegate raw bytes to remote service
            files = {"audio": (filename, raw_bytes)}
            data = {"context_features": "{}"}
            response = await self._async_client.post(
                f"{self._remote_inference_url}/infer/speech", files=files, data=data
            )
            response.raise_for_status()
            result = response.json()
            return result.get("transcription") or result.get("text") or ""

        if self._api_key:
            return await loop.run_in_executor(
                get_io_executor(), self._transcribe_openai_compatible, raw_bytes, filename
            )
        if self._groq_api_key:
            return await loop.run_in_executor(
                get_io_executor(), self._transcribe_groq, raw_bytes, filename
            )
        raise ValueError("No transcription provider configured (set TRANSCRIPTION_API_KEY)")

    def _transcribe_openai_compatible(self, raw_bytes: bytes, filename: str) -> str:
        from openai import OpenAI

        api_key = self._api_key
        if not api_key:
            raise ValueError("TRANSCRIPTION_API_KEY not provided for audio transcription")

        model_id = self._model_id or "qwen3-asr-flash"
        mime_type = mimetypes.guess_type(filename)[0] or "audio/webm"
        data_url = "data:{};base64,{}".format(
            mime_type, base64.b64encode(raw_bytes).decode("utf-8")
        )

        client = OpenAI(api_key=api_key, base_url=self._base_url)
        logger.info(
            "audio_agent_openai_compatible_request model=%s bytes=%s filename=%s base_url=%s",
            model_id,
            len(raw_bytes),
            filename,
            self._base_url,
        )
        messages: list[Any] = [
            {
                "role": "system",
                "content": [{"type": "text", "text": "Singlish, Singapore English."}],
            },
            {
                "role": "user",
                "content": [{"type": "input_audio", "input_audio": {"data": data_url}}],
            },
        ]
        completion = client.chat.completions.create(
            model=model_id,
            messages=messages,
            extra_body={"asr_options": {"language": "en"}},
        )

        message = completion.choices[0].message if completion.choices else None
        content = ""
        if message is not None:
            if getattr(message, "content", None):
                if isinstance(message.content, str):
                    content = message.content
                elif isinstance(message.content, list):
                    parts = []
                    for item in message.content:
                        if isinstance(item, dict) and item.get("text"):
                            parts.append(str(item["text"]))
                    content = " ".join(parts)
            if not content:
                audio = getattr(message, "audio", None)
                transcript = getattr(audio, "transcript", None) if audio is not None else None
                if isinstance(transcript, str):
                    content = transcript

        logger.info("audio_agent_openai_compatible_response length=%s", len(content or ""))
        return (content or "").strip()

    def _transcribe_groq(self, raw_bytes: bytes, filename: str) -> str:
        from groq import Groq

        api_key = self._groq_api_key
        if not api_key:
            raise ValueError("GROQ_API_KEY not provided for audio transcription")

        buf = io.BytesIO(raw_bytes)
        buf.name = filename

        logger.info(
            "audio_agent_groq_request bytes=%s filename=%s",
            len(raw_bytes),
            filename,
        )
        result = Groq(api_key=api_key).audio.transcriptions.create(
            model="whisper-large-v3",
            file=buf,
            prompt="Singlish, Singapore English",
            language="en",
        )
        logger.info("audio_agent_groq_response length=%s", len(result.text or ""))
        return result.text.strip()

    async def close(self) -> None:
        await self._async_client.aclose()
