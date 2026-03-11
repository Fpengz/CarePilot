"""
EmotionAgent
------------
Dual-path emotion analysis for the SEA-LION health assistant.

Pipeline
~~~~~~~~
Audio input
  1. Decode raw bytes → float32 numpy array
  2. Audio heuristic (energy + ZCR) → simulated speech emotion  [MERaLiON placeholder]
  3. j-hartmann/emotion-english-distilroberta-base → text emotion on transcription
  4. Weighted average fusion: speech × 0.60 + text × 0.40

Text input
  → j-hartmann/emotion-english-distilroberta-base only

The resulting EmotionResult can be serialised into a short prompt snippet
(via EmotionAgent.to_context_str) and injected into the LLM system prompt
so the assistant can respond with appropriate empathy.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_TEXT_EMOTION_MODEL    = "j-hartmann/emotion-english-distilroberta-base"

_CONFIDENCE_THRESHOLD = 0.30
# _SAMPLE_RATE, _MAX_AUDIO_SEC, _SPEECH_WEIGHT — only needed for audio decode path (removed)

# j-hartmann raw label → unified label
_TEXT_LABEL_MAP: Dict[str, str] = {
    "anger":   "angry",
    "disgust": "frustrated",
    "fear":    "fearful",
    "joy":     "happy",
    "neutral": "neutral",
    "sadness": "sad",
    "surprise":"confused",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EmotionResult:
    emotion:       str
    score:         float
    input_type:    str                              # "text" | "speech"
    all_scores:    List[Dict[str, float]] = field(default_factory=list)
    transcription: Optional[str]          = None


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class EmotionAgent:
    """
    Lazy-loading, thread-safe emotion classifier.

    Singleton — only one set of model weights is ever resident in memory
    regardless of how many times the class is imported or instantiated.

    Usage::

        agent = EmotionAgent()

        # Text only
        result = agent.analyze_text("I hate these side effects")

        # Audio (raw bytes from HTTP upload + pre-existing transcription)
        result = agent.analyze_audio(raw_bytes, filename="rec.webm",
                                     transcription="I feel terrible today")
    """

    # ── Singleton ────────────────────────────────────────────────────────
    _instance:  Optional["EmotionAgent"] = None
    _init_lock  = threading.Lock()

    # ── Shared model state (class-level) ─────────────────────────────────
    _model_lock    = threading.Lock()
    _text_pipeline = None

    def __new__(cls) -> "EmotionAgent":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    # ====================================================================
    # Public API
    # ====================================================================

    def analyze_text(self, text: str) -> EmotionResult:
        """Text only — runs DistilRoBERTa."""
        emotion, score, all_scores = self._text_emotion(text)
        return EmotionResult(
            emotion=emotion,
            score=round(score, 4),
            input_type="text",
            all_scores=all_scores,
        )

    def analyze_audio(
        self,
        raw_bytes: bytes,
        filename: str = "audio.webm",
        transcription: Optional[str] = None,
    ) -> EmotionResult:
        """
        Audio path — emotion is derived from the Groq transcription text only
        (no audio decoding required). Runs DistilRoBERTa on the transcription.
        """
        if not transcription:
            return EmotionResult(emotion="neutral", score=1.0, input_type="speech")

        emotion, score, all_scores = self._text_emotion(transcription)
        print(f"[EmotionAgent] Audio→text emotion → {emotion} ({score:.2f})")
        return EmotionResult(
            emotion=emotion,
            score=round(score, 4),
            input_type="speech",
            all_scores=all_scores,
            transcription=transcription,
        )

    @staticmethod
    def to_context_str(result: EmotionResult) -> str:
        """Return a short snippet to inject into the LLM system prompt."""
        pct = int(result.score * 100)
        return (
            f"[Emotional context] The user appears to be feeling **{result.emotion}** "
            f"(confidence {pct} %). Please respond with appropriate empathy and tailor "
            f"your advice to their current emotional state."
        )

    # ====================================================================
    # Internal: text emotion
    # ====================================================================

    def _text_emotion(self, text: str) -> Tuple[str, float, List[Dict]]:
        if not text or not text.strip():
            return "neutral", 1.0, []

        pipeline = self._get_text_pipeline()
        raw = pipeline(text[:512])[0]

        # Merge to unified labels (take max per unified label)
        scores: Dict[str, float] = {}
        for item in raw:
            unified = _TEXT_LABEL_MAP.get(item["label"], "neutral")
            scores[unified] = max(scores.get(unified, 0.0), item["score"])

        all_scores = sorted(
            [{"label": k, "score": v} for k, v in scores.items()],
            key=lambda x: x["score"],
            reverse=True,
        )
        top = all_scores[0]
        if top["score"] < _CONFIDENCE_THRESHOLD:
            return "neutral", top["score"], all_scores
        return top["label"], top["score"], all_scores

    # ====================================================================
    # (Audio decode, heuristic speech emotion, and weighted fusion removed.)
    # Audio path now runs DistilRoBERTa on the Groq transcription directly.
    # See the MERaLiON block below if you want to restore a speech model.
    # ====================================================================

    # ====================================================================
    # Model loading (lazy, thread-safe)
    # ====================================================================

    def _get_text_pipeline(self):
        if EmotionAgent._text_pipeline is None:
            with EmotionAgent._model_lock:
                if EmotionAgent._text_pipeline is None:
                    from transformers import pipeline
                    import torch
                    device = 0 if torch.cuda.is_available() else -1
                    print(f"[EmotionAgent] Loading text emotion model: {_TEXT_EMOTION_MODEL}")
                    EmotionAgent._text_pipeline = pipeline(
                        "text-classification",
                        model=_TEXT_EMOTION_MODEL,
                        top_k=None,
                        device=device,
                    )
                    print("[EmotionAgent] Text emotion model loaded ✓")
        return EmotionAgent._text_pipeline

    # ── MERaLiON speech emotion (commented out — too costly to load) ────
    # Uncomment and replace _speech_emotion to use real paralinguistics.
    #
    # _MERALION_EMOTION_REPO = "MERaLiON/MERaLiON-AudioLLM-Whisper-SEA-LION"
    #
    # _meralion_processor = None
    # _meralion_model     = None
    #
    # def _get_meralion(self):
    #     if EmotionAgent._meralion_model is None:
    #         with EmotionAgent._model_lock:
    #             if EmotionAgent._meralion_model is None:
    #                 import torch
    #                 from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
    #                 if torch.backends.mps.is_available():
    #                     device, dtype = "mps", torch.float16
    #                 elif torch.cuda.is_available():
    #                     device, dtype = "cuda", torch.float16
    #                 else:
    #                     device, dtype = "cpu", torch.float32
    #                 EmotionAgent._meralion_processor = AutoProcessor.from_pretrained(
    #                     self._MERALION_EMOTION_REPO, trust_remote_code=True,
    #                 )
    #                 EmotionAgent._meralion_model = AutoModelForSpeechSeq2Seq.from_pretrained(
    #                     self._MERALION_EMOTION_REPO,
    #                     torch_dtype=dtype,
    #                     use_safetensors=True,
    #                     trust_remote_code=True,
    #                 ).to(device)
    #     return EmotionAgent._meralion_processor, EmotionAgent._meralion_model
    #
    # def _speech_emotion_meralion(self, audio_array: np.ndarray) -> Tuple[str, float]:
    #     import torch
    #     _EMOTION_PROMPT = (
    #         "Given the following audio context: <SpeechHere>\n\n"
    #         "Text instruction: Identify the emotion expressed by the speaker. "
    #         "Choose exactly one from: happy, sad, angry, frustrated, anxious, "
    #         "neutral, confused, fearful. Reply with ONLY the emotion label, nothing else."
    #     )
    #     _SYNONYMS = {
    #         "happiness": "happy", "joy": "happy", "joyful": "happy",
    #         "excited": "happy", "cheerful": "happy",
    #         "sadness": "sad", "sorrow": "sad", "depressed": "sad",
    #         "anger": "angry", "rage": "angry", "irritated": "angry",
    #         "furious": "angry", "mad": "angry",
    #         "frustration": "frustrated",
    #         "anxiety": "anxious", "worried": "anxious", "nervous": "anxious",
    #         "stressed": "anxious", "tense": "anxious",
    #         "fear": "fearful", "afraid": "fearful", "scared": "fearful",
    #         "terrified": "fearful", "panic": "fearful",
    #         "confusion": "confused", "uncertain": "confused", "puzzled": "confused",
    #     }
    #     _VALID_LABELS = frozenset(
    #         {"happy", "sad", "angry", "frustrated", "anxious", "neutral", "confused", "fearful"}
    #     )
    #     processor, model = self._get_meralion()
    #     conversation = [{"role": "user", "content": _EMOTION_PROMPT}]
    #     chat_prompt = processor.tokenizer.apply_chat_template(
    #         conversation=conversation, tokenize=False, add_generation_prompt=True,
    #     )
    #     inputs = processor(text=chat_prompt, audios=audio_array, time_duration_limit=_MAX_AUDIO_SEC)
    #     device = next(model.parameters()).device
    #     inputs = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}
    #     with torch.no_grad():
    #         outputs = model.generate(**inputs, max_new_tokens=16)
    #     generated_ids = outputs[:, inputs["input_ids"].size(1):]
    #     raw = processor.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    #     resp = raw.lower().strip()
    #     for word, label in _SYNONYMS.items():
    #         if word in resp:
    #             return label, 0.80
    #     for label in _VALID_LABELS:
    #         if label in resp:
    #             return label, 0.85
    #     return "neutral", 0.50
