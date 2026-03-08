"""
backend/routers/emotion.py
--------------------------
Standalone emotion-analysis endpoints (non-streaming, JSON responses).

POST /api/emotion/text   — { "text": "..." }
     → { emotion, score, all_scores }

POST /api/emotion/audio  — multipart: audio file
     → { emotion, score, transcription, all_scores, input_type }
"""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.deps import audio_agent, emotion_agent

router = APIRouter(prefix="/api/emotion", tags=["emotion"])


class TextEmotionRequest(BaseModel):
    text: str


@router.post("/text")
def analyze_text_emotion(req: TextEmotionRequest):
    """Run DistilRoBERTa emotion analysis on a text string."""
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    result = emotion_agent.analyze_text(req.text)
    return {
        "emotion":    result.emotion,
        "score":      result.score,
        "all_scores": result.all_scores,
        "input_type": result.input_type,
    }


@router.post("/audio")
async def analyze_audio_emotion(audio: UploadFile = File(...)):
    """
    Transcribe audio then run full emotion pipeline:
      MERaLiON speech emotion + DistilRoBERTa on transcription → weighted fusion.
    """
    raw_bytes = await audio.read()
    filename  = audio.filename or "audio.webm"

    # Transcribe first (Groq Whisper via existing AudioAgent)
    try:
        transcription = audio_agent.transcribe_bytes(raw_bytes, filename)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Transcription failed: {exc}")

    result = emotion_agent.analyze_audio(
        raw_bytes, filename, transcription=transcription
    )
    return {
        "emotion":       result.emotion,
        "score":         result.score,
        "transcription": result.transcription,
        "all_scores":    result.all_scores,
        "input_type":    result.input_type,
    }
