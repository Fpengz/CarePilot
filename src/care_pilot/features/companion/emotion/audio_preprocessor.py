"""
Normalize audio inputs for emotion inference.

This module validates and normalizes audio content types used by
emotion classification pipelines.
"""

from __future__ import annotations

import subprocess

SUPPORTED_AUDIO_CONTENT_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/ogg",
    "audio/webm",
    "video/webm",
    "application/octet-stream",
}


def preprocess_audio(
    audio_bytes: bytes,
    *,
    content_type: str | None,
    max_bytes: int = 10 * 1024 * 1024,
) -> bytes:
    if not audio_bytes:
        raise ValueError("audio payload is empty")
    if len(audio_bytes) > max_bytes:
        raise ValueError("audio payload exceeds maximum size")
    lowered = content_type.strip().lower() if content_type else ""
    if lowered and ";" in lowered:
        lowered = lowered.split(";", 1)[0].strip()
    if lowered:
        if lowered not in SUPPORTED_AUDIO_CONTENT_TYPES:
            raise ValueError("unsupported audio format")
        if lowered in {"audio/webm", "video/webm"}:
            return _convert_webm_to_wav(audio_bytes)
    return audio_bytes


def _convert_webm_to_wav(audio_bytes: bytes) -> bytes:
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-i",
                "pipe:0",
                "-f",
                "wav",
                "-ac",
                "1",
                "-ar",
                "16000",
                "pipe:1",
            ],
            input=audio_bytes,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise ValueError("ffmpeg is required to decode webm audio") from exc
    except subprocess.CalledProcessError as exc:
        raise ValueError("failed to decode webm audio") from exc
    if not result.stdout:
        raise ValueError("decoded audio is empty")
    return result.stdout
