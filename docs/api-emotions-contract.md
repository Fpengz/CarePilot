# API Emotion Contracts & Workflow

## Purpose
The Emotion Pipeline provides structured emotional analysis of user interactions (text and speech) to support the ChatAgent and Clinical Digest. It uses a multimodal architecture to combine linguistic content with acoustic signals, producing a unified product-safe emotional state that avoids raw model overreaction.

## Architecture Overview

```mermaid
flowchart TD
    A[User Input] --> B[API Router / Orchestrator]
    B --> C[EmotionPipeline]
    
    C --> D[TextEmotionBranch]
    C --> E[SpeechEmotionBranch]
    E --> F[ASR (Whisper/MERaLiON)]
    
    C --> G[ContextFeatureExtractor]
    G --> H[EventTimeline History]
    
    D --> I[EmotionFusion]
    E --> I
    G --> I
    
    I --> J[EmotionInferenceResult]
    J --> K[Downstream Consumers / ChatAgent]
```

### Module Responsibilities

1. **Orchestrator (`features/companion/chat/use_cases`)**:
   - Decides when emotion inference is needed.
   - Collects user input (text/audio).
   - Invokes the `EmotionAgent` which wraps the inference pipeline.
   
2. **EmotionPipeline (`features/companion/emotion/pipeline.py`)**:
   - Coordinates branch execution.
   - Collects outputs from ASR, Speech, Text, and Context.
   - Invokes Fusion and generates `EmotionInferenceResult`.
   
3. **Branches (`features/companion/emotion/adapters/*`)**:
   - Executes domain-specific inference logic (e.g. RoBERTa for text, HuBERT for speech).
   
4. **ContextFeatureExtractor (`features/companion/emotion/context/*`)**:
   - Queries the canonical `EventTimelineService` to establish recent user emotional trends (e.g. `worsening`, `improving`).
   
5. **FusionLayer (`features/companion/emotion/adapters/fusion_hf.py`)**:
   - Concatenates the features (text logits, speech logits, context trend).
   - Predicts a unified `EmotionLabel` and a safer `EmotionProductState` (e.g. `needs_reassurance`).
   
6. **Contracts (`agent/emotion/schemas.py`)**:
   - Defines strict typed Pydantic models for inputs and traces.

## Contract Definitions

### `EmotionInferenceResult`
The final payload passed back to the app and saved to the timeline.

```json
{
  "source_type": "mixed",
  "final_emotion": "frustrated",
  "product_state": "distressed",
  "confidence": 0.89,
  "text_branch": {
    "transcript_or_text": "I can't get this to work.",
    "emotion_scores": {"frustrated": 0.82, "sad": 0.1},
    "predicted_emotion": "frustrated",
    "confidence": 0.82,
    "model_name": "kashyaparun/Mental-Health-Chatbot-using-RoBERTa",
    "metadata": {"adapter": "hf"}
  },
  "speech_branch": {
    "raw_audio_reference": null,
    "transcription": "I can't get this to work.",
    "acoustic_scores": {"duration_sec": 3.4},
    "predicted_emotion": "frustrated",
    "emotion_scores": {"frustrated": 0.91},
    "confidence": 0.91,
    "asr_metadata": {},
    "model_name": "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition",
    "metadata": {"adapter": "hf"}
  },
  "context_features": {
    "recent_labels": ["sad", "frustrated"],
    "trend": "worsening",
    "recent_product_states": []
  },
  "fusion_method": "hf-text-classification-head",
  "model_metadata": {
    "text_model": "kashyaparun/...",
    "speech_model": "ehcalabres/..."
  },
  "trace": {
    "fusion_inputs": {...},
    "weighting_strategy": "hf-text-classification-head",
    "conflict_resolution": "argmax",
    "final_decision_reason": "Top fused score was 0.89 for frustrated"
  }
}
```

## Integration Points
- **API Router**: `/api/v1/emotions/text` and `/api/v1/emotions/speech` handle REST ingestion.
- **Agent Logging**: Responses are written as `emotion_observed` events into the `EventTimelineService`.

## Testing Expectations
- **Isolation**: Text, Speech, and Fusion adapters should be independently mockable via `TextEmotionPort`, `SpeechEmotionPort`, and `FusionPort`.
- **Traceability**: All branch execution metadata must be present in the `trace` dict for downstream ML ops benchmarking.
