"""
Transcribe audio inputs for the chat agent.

This module provides audio transcription helpers backed by Groq Whisper
or a local MERaLiON model for Singapore-English speech.

Example:
    agent = AudioAgent()
    text = agent.transcribe_groq(audio_input)
"""

import base64
import io
import logging
import mimetypes

import librosa
import numpy as np
import soundfile as sf
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

from care_pilot.platform.observability import get_logger

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
    ) -> None:
        self.repo_id = repo_id or "MERaLiON/MERaLiON-2-3B"
        self._groq_api_key = groq_api_key
        self._provider = (provider or "").strip().lower()
        self._api_key = api_key
        self._base_url = base_url
        self._model_id = model_id
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.torch_dtype = torch.float16 if torch.backends.mps.is_available() else torch.float32
        self.processor = None
        self.model = None

    # ------------------------------------------------------------------
    # MERaLiON (local)
    # ------------------------------------------------------------------

    def load_model(self) -> None:
        """Download & load the MERaLiON model onto the local device."""
        logger.info(
            "audio_agent_load_start repo_id=%s device=%s",
            self.repo_id,
            self.device,
        )
        self.processor = AutoProcessor.from_pretrained(self.repo_id, trust_remote_code=True)
        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
            self.repo_id,
            torch_dtype=self.torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True,
            trust_remote_code=True,
        ).to(self.device)
        logger.info("audio_agent_load_complete repo_id=%s", self.repo_id)

    def transcribe(self, audio_input: tuple) -> str:
        """Transcribe audio using the local MERaLiON model.

        Args:
            audio_input: (sample_rate, np.ndarray) from gr.Audio.

        Returns:
            Transcribed text string.
        """
        if self.model is None or self.processor is None:
            return "[MERaLiON] Model not loaded — call load_model() first."

        if audio_input is None:
            return "Error: No audio provided."

        sample_rate, audio_array = audio_input
        if sample_rate != 16000:
            audio_array = librosa.resample(
                y=audio_array.astype(np.float32),
                orig_sr=sample_rate,
                target_sr=16000,
            )

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
    # Groq Whisper (cloud)
    # ------------------------------------------------------------------

    def transcribe_bytes(self, raw_bytes: bytes, filename: str = "audio.webm") -> str:
        """Transcribe raw audio bytes (webm/mp3/wav/ogg) via OpenAI-compatible ASR."""
        provider = self._provider
        if provider in {"groq"}:
            return self._transcribe_groq(raw_bytes, filename=filename)
        if provider in {"qwen", "openai", "openai-compatible", "compatible"}:
            return self._transcribe_openai_compatible(raw_bytes, filename=filename)
        if self._api_key:
            return self._transcribe_openai_compatible(raw_bytes, filename=filename)
        if self._groq_api_key:
            return self._transcribe_groq(raw_bytes, filename=filename)
        raise ValueError("No transcription provider configured (set TRANSCRIPTION_API_KEY)")

    def _transcribe_openai_compatible(self, raw_bytes: bytes, *, filename: str) -> str:
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
        openai_logger = logging.getLogger("openai")
        openai_base_logger = logging.getLogger("openai._base_client")
        httpx_logger = logging.getLogger("httpx")
        httpcore_logger = logging.getLogger("httpcore")
        prev_levels = {
            "openai": openai_logger.level,
            "openai._base_client": openai_base_logger.level,
            "httpx": httpx_logger.level,
            "httpcore": httpcore_logger.level,
        }
        # Avoid logging full audio payloads in debug traces.
        openai_logger.setLevel(logging.INFO)
        openai_base_logger.setLevel(logging.INFO)
        httpx_logger.setLevel(logging.INFO)
        httpcore_logger.setLevel(logging.INFO)
        logger.info(
            "audio_agent_openai_compatible_request model=%s bytes=%s filename=%s base_url=%s",
            model_id,
            len(raw_bytes),
            filename,
            self._base_url,
        )
        try:
            from typing import Any

            messages: list[Any] = [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": "Singlish, Singapore English.",
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {"data": data_url},
                        }
                    ],
                },
            ]
            completion = client.chat.completions.create(
                model=model_id,
                messages=messages,
                extra_body={"asr_options": {"language": "en"}},
            )
        finally:
            openai_logger.setLevel(prev_levels["openai"])
            openai_base_logger.setLevel(prev_levels["openai._base_client"])
            httpx_logger.setLevel(prev_levels["httpx"])
            httpcore_logger.setLevel(prev_levels["httpcore"])

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

    def _transcribe_groq(self, raw_bytes: bytes, *, filename: str) -> str:
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

    def transcribe_groq(self, audio_input: tuple) -> str:
        """Transcribe audio using the Groq Whisper API (cloud, very fast).

        Audio is converted to a WAV buffer in memory and sent to Groq.
        Returns the plain transcribed text string — NOT an LLM response.

        Args:
            audio_input: (sample_rate, np.ndarray) from gr.Audio.

        Returns:
            Transcribed text string.
        """
        from groq import Groq

        api_key = self._groq_api_key
        if not api_key:
            return "Error: GROQ_API_KEY not provided for audio transcription"

        if audio_input is None:
            return "Error: No audio provided."

        sample_rate, audio_array = audio_input
        audio_array = audio_array.astype(np.float32)
        if sample_rate != 16000:
            audio_array = librosa.resample(y=audio_array, orig_sr=sample_rate, target_sr=16000)

        buffer = io.BytesIO()
        sf.write(buffer, audio_array, 16000, format="WAV")
        buffer.seek(0)
        buffer.name = "audio.wav"  # required by Groq SDK

        logger.info("audio_agent_groq_request buffered=True")
        client = Groq(api_key=api_key)
        result = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=buffer,
            prompt="Singlish, Singapore English",
            language="en",
        )
        logger.info("audio_agent_groq_response length=%s", len(result.text or ""))
        return result.text
