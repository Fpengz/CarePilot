"""
Standalone Emotion & Audio Inference Service.

This service hosts heavy ML models (Whisper, BERT, MERaLiON) and exposes
them via an async FastAPI layer to prevent GIL-blocking in the main API.
"""

from __future__ import annotations

import asyncio
import io
from typing import Annotated, Any, cast

import librosa
import torch
from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

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
from care_pilot.platform.runtime.executors import get_ml_executor
from care_pilot.platform.runtime.hf_loader import get_hf_loader

app = FastAPI(title="CarePilot Inference Service")

# Setup models
settings = get_settings()
config = EmotionRuntimeConfig.from_settings(settings)
device = config.model_device
if device == "auto":
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

emotion_pipeline = EmotionPipeline(
    asr=WhisperASR(config.asr_model_id, device),
    text=HFTextEmotion(config.text_model_id, device),
    speech=HFSpeechEmotion(config.speech_model_id, device),
    context=context_extractor,
    fusion=build_fusion(config, device),
)

# Shared ASR model for AudioAgent (MERaLiON)
asr_repo = "MERaLiON/MERaLiON-2-3B"
asr_processor = get_hf_loader(asr_repo, load_func=cast(Any, AutoProcessor.from_pretrained), trust_remote_code=True)
asr_model = get_hf_loader(
    asr_repo,
    load_func=cast(Any, AutoModelForSpeechSeq2Seq.from_pretrained),
    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    trust_remote_code=True
).to(device)

class TextInferenceRequest(BaseModel):
    text: str
    language: str | None = None
    user_id: str | None = None
    context_features: EmotionContextFeatures

@app.post("/infer/text", response_model=EmotionInferenceResult)
async def infer_text(request: TextInferenceRequest):
    context_extractor.set_features(request.context_features)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        get_ml_executor(),
        emotion_pipeline.infer_text,
        request.text,
        request.language,
        request.user_id
    )

@app.post("/infer/speech", response_model=EmotionInferenceResult)
async def infer_speech(
    audio: Annotated[UploadFile, File()],
    user_id: Annotated[str | None, Form()] = None,
    language: Annotated[str | None, Form()] = None,
    transcription: Annotated[str | None, Form()] = None,
    context_features: Annotated[str, Form()] = "{}",
):
    features = EmotionContextFeatures.model_validate_json(context_features)
    context_extractor.set_features(features)

    audio_bytes = await audio.read()
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        get_ml_executor(),
        emotion_pipeline.infer_speech,
        audio_bytes,
        audio.filename,
        language,
        transcription,
        user_id
    )

def _transcribe_meralion_sync(audio_bytes: bytes) -> str:
    # Basic audio load
    with io.BytesIO(audio_bytes) as buf:
        audio_array, sample_rate = librosa.load(buf, sr=16000)

    conversation = [[{"role": "user", "content": "Please transcribe this speech."}]]
    chat_prompt = asr_processor.tokenizer.apply_chat_template(
        conversation=conversation, tokenize=False, add_generation_prompt=True
    )
    inputs = asr_processor(text=chat_prompt, audios=[audio_array], return_tensors="pt").to(device)
    if device == "cuda":
        inputs["input_features"] = inputs["input_features"].to(torch.float16)

    generated_ids = asr_model.generate(**inputs, max_new_tokens=256)
    return asr_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

@app.post("/transcribe")
async def transcribe(audio: Annotated[UploadFile, File()]):
    audio_bytes = await audio.read()
    loop = asyncio.get_running_loop()
    text = await loop.run_in_executor(get_ml_executor(), _transcribe_meralion_sync, audio_bytes)
    return {"text": text}

@app.get("/health", response_model=EmotionRuntimeHealth)
async def health():
    return EmotionRuntimeHealth(
        status="ready",
        model_cache_ready=True,
        source_commit=config.source_commit,
        detail="Remote inference service active (Emotion + ASR)"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
