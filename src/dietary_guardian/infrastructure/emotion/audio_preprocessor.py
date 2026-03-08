from __future__ import annotations


SUPPORTED_AUDIO_CONTENT_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/ogg",
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
    if content_type:
        lowered = content_type.strip().lower()
        if lowered and lowered not in SUPPORTED_AUDIO_CONTENT_TYPES:
            raise ValueError("unsupported audio format")
    return audio_bytes

