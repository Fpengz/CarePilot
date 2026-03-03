"""
AudioAgent
----------
Responsible for transcribing audio input into text.

Supported backends:
  • Groq Whisper  – cloud-based, fast (default)
  • MERaLiON     – local model, Singapore-English focused

Usage
-----
    agent = AudioAgent()
    text = agent.transcribe_groq(audio_input)   # (sample_rate, np.ndarray)
    text = agent.transcribe(audio_input)         # MERaLiON (load_model() first)
"""

import io
import os

import librosa
import numpy as np
import soundfile as sf
import torch
from dotenv import load_dotenv
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

load_dotenv()

_PROMPT_TEMPLATE = (
    "Instruction: {query} \n"
    "Follow the text instruction based on the following audio: <SpeechHere>"
)
_TRANSCRIBE_PROMPT = "Please transcribe this speech."


class AudioAgent:
    """Agent that transcribes audio to text using Groq Whisper or MERaLiON."""

    def __init__(self, repo_id: str | None = None) -> None:
        self.repo_id = repo_id or os.environ.get(
            "TRANSCRIPTION_MODEL_ID", "MERaLiON/MERaLiON-2-3B"
        )
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.torch_dtype = (
            torch.float16 if torch.backends.mps.is_available() else torch.float32
        )
        self.processor = None
        self.model = None

    # ------------------------------------------------------------------
    # MERaLiON (local)
    # ------------------------------------------------------------------

    def load_model(self) -> None:
        """Download & load the MERaLiON model onto the local device."""
        print(f"[AudioAgent] Loading '{self.repo_id}' on '{self.device}'…")
        self.processor = AutoProcessor.from_pretrained(
            self.repo_id, trust_remote_code=True
        )
        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
            self.repo_id,
            torch_dtype=self.torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True,
            trust_remote_code=True,
        ).to(self.device)
        print("[AudioAgent] MERaLiON model loaded.")

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
                y=audio_array.astype(np.float32), orig_sr=sample_rate, target_sr=16000
            )

        conversation = [
            [{"role": "user", "content": _PROMPT_TEMPLATE.format(query=_TRANSCRIBE_PROMPT)}]
        ]
        chat_prompt = self.processor.tokenizer.apply_chat_template(
            conversation=conversation, tokenize=False, add_generation_prompt=True
        )

        inputs = self.processor(
            text=chat_prompt, audios=[audio_array], return_tensors="pt"
        ).to(self.device)
        inputs["input_features"] = inputs["input_features"].to(self.torch_dtype)

        generated_ids = self.model.generate(**inputs, max_new_tokens=256)
        return self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

    # ------------------------------------------------------------------
    # Groq Whisper (cloud)
    # ------------------------------------------------------------------

    def transcribe_bytes(self, raw_bytes: bytes, filename: str = "audio.webm") -> str:
        """Transcribe raw audio bytes (webm/mp3/wav/ogg) via Groq Whisper.

        This is the preferred method for the FastAPI backend where the browser
        sends a webm blob directly — no NumPy / sample-rate conversion needed.

        Args:
            raw_bytes: Raw audio file content from the HTTP upload.
            filename:  Original filename (used to hint the codec to Groq).

        Returns:
            Transcribed text string.

        Raises:
            ValueError: If GROQ_API_KEY is not set or transcription fails.
        """
        from groq import Groq

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in environment")

        buf = io.BytesIO(raw_bytes)
        buf.name = filename

        print(f"[AudioAgent] Sending {len(raw_bytes)} bytes ({filename}) to Groq Whisper…")
        result = Groq(api_key=api_key).audio.transcriptions.create(
            model="whisper-large-v3",
            file=buf,
            prompt="Singlish, Singapore English",
            language="en",
        )
        print(f"[AudioAgent] Transcription: {result.text!r}")
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

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return "Error: GROQ_API_KEY not set in .env"

        if audio_input is None:
            return "Error: No audio provided."

        sample_rate, audio_array = audio_input
        audio_array = audio_array.astype(np.float32)
        if sample_rate != 16000:
            audio_array = librosa.resample(
                y=audio_array, orig_sr=sample_rate, target_sr=16000
            )

        buffer = io.BytesIO()
        sf.write(buffer, audio_array, 16000, format="WAV")
        buffer.seek(0)
        buffer.name = "audio.wav"  # required by Groq SDK

        print("[AudioAgent] Sending audio to Groq Whisper…")
        client = Groq(api_key=api_key)
        result = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=buffer,
            prompt="Singlish, Singapore English",
            language="en",
        )
        print(f"[AudioAgent] Transcription: {result.text!r}")
        return result.text
