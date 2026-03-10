"""Emotion and coaching-tone settings for companion response behavior."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmotionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EMOTION_", extra="ignore", case_sensitive=False, populate_by_name=True)

    inference_enabled: bool = False
    speech_enabled: bool = False
    request_timeout_seconds: float = Field(default=15.0, ge=0.1, le=300.0)
    model_device: Literal["auto", "cpu", "cuda"] = "auto"
    text_model_id: str = "j-hartmann/emotion-english-distilroberta-base"
    speech_model_id: str = "meralion/speech-emotion-recognition"
    source_commit: str = "9afc3f1a3a3fec71a4e5920d8f4103710b337ecc"
