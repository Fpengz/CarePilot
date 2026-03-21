"""
Standalone Emotion Inference Service.

This service hosts the heavy ML models (Whisper, BERT) for emotion detection
and exposes them via a thin FastAPI layer.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel

from care_pilot.agent.emotion.schemas import (
    EmotionContextFeatures,
    EmotionInferenceResult,
    EmotionRuntimeHealth,
)
from care_pilot.config.app import get_settings
from care_pilot.features.companion.emotion.adapters.asr_whisper import WhisperASR
from care_pilot.features.companion.emotion.adapters.fusion_hf import HFFusion
from care_pilot.features.companion.emotion.adapters.speech_hf import HFSpeechEmotion
from care_pilot.features.companion.emotion.adapters.text_hf import HFTextEmotion
from care_pilot.features.companion.emotion.config import EmotionRuntimeConfig
from care_pilot.features.companion.emotion.fusion.heuristic_fusion import HeuristicFusion
from care_pilot.features.companion.emotion.pipeline import EmotionPipeline
from care_pilot.features.companion.emotion.ports import ContextFeaturePort, FusionPort

app = FastAPI(title="CarePilot Emotion Inference Service")

# Setup models
settings = get_settings()
config = EmotionRuntimeConfig.from_settings(settings)
device = config.model_device
if device == "auto":
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"

class StaticContextExtractor(ContextFeaturePort):
    """Simple extractor that returns provided features."""
    def __init__(self):
        self.current_features = EmotionContextFeatures(
            recent_labels=[], trend="stable", recent_product_states=[]
        )

    def extract(self, user_id: str | None) -> EmotionContextFeatures:
        del user_id
        return self.current_features

    def set_features(self, features: EmotionContextFeatures):
        self.current_features = features

context_extractor = StaticContextExtractor()

def build_fusion(config: EmotionRuntimeConfig, device: str) -> FusionPort:
    if not config.fusion_model_id:
        return HeuristicFusion()
    try:
        return HFFusion(config.fusion_model_id, device)
    except Exception:
        return HeuristicFusion()

pipeline = EmotionPipeline(
    asr=WhisperASR(config.asr_model_id, device),
    text=HFTextEmotion(config.text_model_id, device),
    speech=HFSpeechEmotion(config.speech_model_id, device),
    context=context_extractor,
    fusion=build_fusion(config, device),
)

class TextInferenceRequest(BaseModel):
    text: str
    language: str | None = None
    user_id: str | None = None
    context_features: EmotionContextFeatures

@app.post("/infer/text", response_model=EmotionInferenceResult)
async def infer_text(request: TextInferenceRequest):
    context_extractor.set_features(request.context_features)
    return pipeline.infer_text(
        text=request.text,
        language=request.language,
        user_id=request.user_id
    )

@app.post("/infer/speech", response_model=EmotionInferenceResult)
async def infer_speech(
    audio: Annotated[UploadFile, File()],
    user_id: Annotated[str | None, Form()] = None,
    language: Annotated[str | None, Form()] = None,
    transcription: Annotated[str | None, Form()] = None,
    context_features: Annotated[str, Form()] = "{}",
):
    # Parse context features from string form data
    features = EmotionContextFeatures.model_validate_json(context_features)
    context_extractor.set_features(features)

    audio_bytes = await audio.read()
    return pipeline.infer_speech(
        audio_bytes=audio_bytes,
        filename=audio.filename,
        language=language,
        transcription=transcription,
        user_id=user_id
    )

@app.get("/health", response_model=EmotionRuntimeHealth)
async def health():
    return EmotionRuntimeHealth(
        status="ready",
        model_cache_ready=True,
        source_commit=config.source_commit,
        detail="Remote inference service active"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
