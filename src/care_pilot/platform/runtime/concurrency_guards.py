"""
Provide concurrency guards and backpressure mechanisms.

This module uses semaphores to limit the number of concurrent heavy tasks,
preventing system exhaustion under burst load.
"""

import asyncio
from typing import Final

# Limit concurrent ML inferences to prevent CPU/Memory exhaustion
# These should align with the ML thread pool size but act as an async-side guard.
MAX_CONCURRENT_EMOTION_TEXT: Final[int] = 4
MAX_CONCURRENT_EMOTION_SPEECH: Final[int] = 2

# Semaphores are initialized lazily within an async context
_EMOTION_TEXT_SEMAPHORE: asyncio.Semaphore | None = None
_EMOTION_SPEECH_SEMAPHORE: asyncio.Semaphore | None = None

def get_emotion_text_semaphore() -> asyncio.Semaphore:
    global _EMOTION_TEXT_SEMAPHORE
    if _EMOTION_TEXT_SEMAPHORE is None:
        _EMOTION_TEXT_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_EMOTION_TEXT)
    return _EMOTION_TEXT_SEMAPHORE

def get_emotion_speech_semaphore() -> asyncio.Semaphore:
    global _EMOTION_SPEECH_SEMAPHORE
    if _EMOTION_SPEECH_SEMAPHORE is None:
        _EMOTION_SPEECH_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_EMOTION_SPEECH)
    return _EMOTION_SPEECH_SEMAPHORE
