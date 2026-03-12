# Emotion Pipeline Refactor Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement an injectable, multimodal emotion pipeline with full-trace API responses and timeline-derived context features.

**Architecture:** Add a pipeline orchestrator with ports for ASR, text, speech, and fusion. Replace the emotion inference contract with a full trace and update API adapters and tests to the new schema.

**Tech Stack:** FastAPI, Pydantic v2, Transformers (HF), Torch, librosa, existing timeline service.

---

## File Structure (Planned)
- Modify: `src/dietary_guardian/features/companion/core/health/emotion.py`
- Modify: `src/dietary_guardian/agent/emotion/agent.py`
- Modify: `src/dietary_guardian/agent/emotion/runtime.py`
- Create: `src/dietary_guardian/agent/emotion/pipeline.py`
- Create: `src/dietary_guardian/agent/emotion/ports.py`
- Create: `src/dietary_guardian/agent/emotion/adapters/asr_meralion.py`
- Create: `src/dietary_guardian/agent/emotion/adapters/text_hf.py`
- Create: `src/dietary_guardian/agent/emotion/adapters/speech_hf.py`
- Create: `src/dietary_guardian/agent/emotion/adapters/fusion_hf.py`
- Modify: `apps/api/dietary_api/schemas/core.py`
- Modify: `apps/api/dietary_api/services/emotion_session.py`
- Modify: `apps/api/dietary_api/routers/emotions.py`
- Modify: `docs/api-emotions-contract.md`
- Modify: `tests/capabilities/test_emotion_service.py`
- Modify: `tests/api/test_api_emotions.py`

---

## Chunk 1: Domain Contract + Schemas

### Task 1: Replace Emotion Domain Contract With Full Trace

**Files:**
- Modify: `src/dietary_guardian/features/companion/core/health/emotion.py`
- Modify: `apps/api/dietary_api/schemas/core.py`
- Test: `tests/capabilities/test_emotion_service.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/capabilities/test_emotion_service.py

def test_emotion_trace_includes_fusion_and_context() -> None:
    result = EmotionInferenceResult(
        text_branch=EmotionTextBranch(
            transcript="hello",
            model_name="text-model",
            model_version="1",
            scores={"neutral": 0.7},
        ),
        speech_branch=EmotionSpeechBranch(
            transcript="hello",
            model_name="speech-model",
            model_version="1",
            scores={"neutral": 0.6},
            acoustic_summary={"duration_sec": 1.2},
        ),
        context_features=EmotionContextFeatures(
            recent_labels=["neutral"],
            trend="stable",
        ),
        fusion=EmotionFusionOutput(
            emotion_label="neutral",
            product_state="stable",
            confidence=0.72,
            logits={"neutral": 0.72},
        ),
        source_type="mixed",
    )
    assert result.fusion.product_state == "stable"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/capabilities/test_emotion_service.py::test_emotion_trace_includes_fusion_and_context`
Expected: FAIL with `NameError` or schema mismatch.

- [ ] **Step 3: Write minimal implementation**

```python
# src/dietary_guardian/features/companion/core/health/emotion.py

class EmotionProductState(StrEnum):
    STABLE = "stable"
    NEEDS_REASSURANCE = "needs_reassurance"
    CONFUSED = "confused"
    DISTRESSED = "distressed"
    URGENT_REVIEW = "urgent_review"

class EmotionTextBranch(BaseModel):
    transcript: str
    model_name: str
    model_version: str
    scores: dict[EmotionLabel, float]

class EmotionSpeechBranch(BaseModel):
    transcript: str | None = None
    model_name: str
    model_version: str
    scores: dict[EmotionLabel, float]
    acoustic_summary: dict[str, float] = Field(default_factory=dict)

class EmotionContextFeatures(BaseModel):
    recent_labels: list[EmotionLabel] = Field(default_factory=list)
    trend: Literal["worsening", "stable", "improving"]

class EmotionFusionOutput(BaseModel):
    emotion_label: EmotionLabel
    product_state: EmotionProductState
    confidence: float = Field(ge=0.0, le=1.0)
    logits: dict[EmotionLabel, float] = Field(default_factory=dict)

class EmotionInferenceResult(BaseModel):
    source_type: Literal["text", "speech", "mixed"]
    text_branch: EmotionTextBranch | None = None
    speech_branch: EmotionSpeechBranch | None = None
    context_features: EmotionContextFeatures
    fusion: EmotionFusionOutput
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

Update `apps/api/dietary_api/schemas/core.py` to mirror the new response structure and update response models accordingly.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -q tests/capabilities/test_emotion_service.py::test_emotion_trace_includes_fusion_and_context`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dietary_guardian/features/companion/core/health/emotion.py apps/api/dietary_api/schemas/core.py tests/capabilities/test_emotion_service.py
git commit -m "feat: add emotion trace domain contract"
```

---

## Chunk 2: Injectable Pipeline + Ports

### Task 2: Add Ports and Pipeline Orchestrator

**Files:**
- Create: `src/dietary_guardian/agent/emotion/ports.py`
- Create: `src/dietary_guardian/agent/emotion/pipeline.py`
- Modify: `src/dietary_guardian/agent/emotion/runtime.py`
- Test: `tests/capabilities/test_emotion_service.py`

- [ ] **Step 1: Write failing test**

```python
# tests/capabilities/test_emotion_service.py

class _StubASR:
    def transcribe(self, audio_bytes: bytes, *, filename: str | None, language: str | None) -> str:
        return "hello"

class _StubText:
    def predict(self, text: str, language: str | None) -> tuple[dict[str, float], str, str]:
        return {"neutral": 0.7}, "text-model", "1"

class _StubSpeech:
    def predict(self, audio_bytes: bytes, *, transcript: str | None) -> tuple[dict[str, float], dict[str, float], str, str]:
        return {"neutral": 0.6}, {"duration_sec": 1.2}, "speech-model", "1"

class _StubFusion:
    def predict(self, *, text_scores, speech_scores, context) -> tuple[str, str, float, dict[str, float]]:
        return "neutral", "stable", 0.72, {"neutral": 0.72}


def test_pipeline_runs_with_ports() -> None:
    pipeline = EmotionPipeline(
        asr=_StubASR(), text=_StubText(), speech=_StubSpeech(), fusion=_StubFusion()
    )
    result = pipeline.infer_speech(audio_bytes=b"fake", filename=None, language=None, transcription=None, context={})
    assert result.fusion.product_state == "stable"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/capabilities/test_emotion_service.py::test_pipeline_runs_with_ports`
Expected: FAIL with `NameError`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/dietary_guardian/agent/emotion/ports.py

class ASRPort(Protocol):
    def transcribe(self, audio_bytes: bytes, *, filename: str | None, language: str | None) -> str: ...

class TextEmotionPort(Protocol):
    def predict(self, text: str, language: str | None) -> tuple[dict[EmotionLabel, float], str, str]: ...

class SpeechEmotionPort(Protocol):
    def predict(
        self,
        audio_bytes: bytes,
        *,
        transcript: str | None,
    ) -> tuple[dict[EmotionLabel, float], dict[str, float], str, str]: ...

class FusionPort(Protocol):
    def predict(
        self,
        *,
        text_scores: dict[EmotionLabel, float],
        speech_scores: dict[EmotionLabel, float] | None,
        context: EmotionContextFeatures,
    ) -> tuple[EmotionLabel, EmotionProductState, float, dict[EmotionLabel, float]]: ...
```

```python
# src/dietary_guardian/agent/emotion/pipeline.py

class EmotionPipeline:
    def __init__(self, *, asr: ASRPort, text: TextEmotionPort, speech: SpeechEmotionPort, fusion: FusionPort) -> None:
        self._asr = asr
        self._text = text
        self._speech = speech
        self._fusion = fusion

    def infer_text(self, *, text: str, language: str | None, context: EmotionContextFeatures) -> EmotionInferenceResult:
        scores, model_name, model_version = self._text.predict(text, language)
        fusion_label, product_state, confidence, logits = self._fusion.predict(
            text_scores=scores,
            speech_scores=None,
            context=context,
        )
        return EmotionInferenceResult(
            source_type="text",
            text_branch=EmotionTextBranch(
                transcript=text,
                model_name=model_name,
                model_version=model_version,
                scores=scores,
            ),
            speech_branch=None,
            context_features=context,
            fusion=EmotionFusionOutput(
                emotion_label=fusion_label,
                product_state=product_state,
                confidence=confidence,
                logits=logits,
            ),
        )

    def infer_speech(self, *, audio_bytes: bytes, filename: str | None, language: str | None, transcription: str | None, context: EmotionContextFeatures) -> EmotionInferenceResult:
        transcript = self._asr.transcribe(audio_bytes, filename=filename, language=language)
        scores, acoustic, model_name, model_version = self._speech.predict(audio_bytes, transcript=transcript)
        text_scores, text_model_name, text_model_version = self._text.predict(transcript, language)
        fusion_label, product_state, confidence, logits = self._fusion.predict(
            text_scores=text_scores,
            speech_scores=scores,
            context=context,
        )
        return EmotionInferenceResult(
            source_type="mixed",
            text_branch=EmotionTextBranch(
                transcript=transcript,
                model_name=text_model_name,
                model_version=text_model_version,
                scores=text_scores,
            ),
            speech_branch=EmotionSpeechBranch(
                transcript=transcript,
                model_name=model_name,
                model_version=model_version,
                scores=scores,
                acoustic_summary=acoustic,
            ),
            context_features=context,
            fusion=EmotionFusionOutput(
                emotion_label=fusion_label,
                product_state=product_state,
                confidence=confidence,
                logits=logits,
            ),
        )
```

Update `runtime.py` to compose the pipeline and call it instead of the old engine.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -q tests/capabilities/test_emotion_service.py::test_pipeline_runs_with_ports`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dietary_guardian/agent/emotion/ports.py src/dietary_guardian/agent/emotion/pipeline.py src/dietary_guardian/agent/emotion/runtime.py tests/capabilities/test_emotion_service.py
git commit -m "feat: add injectable emotion pipeline"
```

---

## Chunk 3: Model Adapters + Settings

### Task 3: Add HF-backed adapters and MERaLiON ASR

**Files:**
- Create: `src/dietary_guardian/agent/emotion/adapters/asr_meralion.py`
- Create: `src/dietary_guardian/agent/emotion/adapters/text_hf.py`
- Create: `src/dietary_guardian/agent/emotion/adapters/speech_hf.py`
- Create: `src/dietary_guardian/agent/emotion/adapters/fusion_hf.py`
- Modify: `src/dietary_guardian/config/runtime.py`
- Modify: `src/dietary_guardian/agent/emotion/runtime.py`

- [ ] **Step 1: Write failing test**

```python
# tests/capabilities/test_emotion_service.py

def test_runtime_raises_not_configured_when_fusion_missing() -> None:
    settings = EmotionRuntimeConfig(
        text_model_id="text",
        speech_model_id="speech",
        model_device="cpu",
        source_commit="sha",
        fusion_model_id=None,
        asr_model_id="MERaLiON/MERaLiON-2-3B",
    )
    runtime = InProcessEmotionRuntime(settings)
    with pytest.raises(ValueError):
        runtime.infer_text(TextEmotionInput(text="hello"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/capabilities/test_emotion_service.py::test_runtime_raises_not_configured_when_fusion_missing`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```python
# src/dietary_guardian/config/runtime.py

class EmotionSettings(BaseSettings):
    ...
    asr_model_id: str = "MERaLiON/MERaLiON-2-3B"
    fusion_model_id: str | None = None
    history_window: int = Field(default=5, ge=1, le=20)
```

```python
# src/dietary_guardian/agent/emotion/adapters/asr_meralion.py

class MeralionASR(ASRPort):
    def __init__(self, repo_id: str) -> None: ...
    def transcribe(self, audio_bytes: bytes, *, filename: str | None, language: str | None) -> str: ...
```

```python
# src/dietary_guardian/agent/emotion/adapters/text_hf.py

class HFTextEmotion(TextEmotionPort):
    def __init__(self, model_id: str, device: str) -> None: ...
    def predict(self, text: str, language: str | None) -> tuple[dict[EmotionLabel, float], str, str]: ...
```

```python
# src/dietary_guardian/agent/emotion/adapters/speech_hf.py

class HFSpeechEmotion(SpeechEmotionPort):
    def __init__(self, model_id: str, device: str) -> None: ...
    def predict(self, audio_bytes: bytes, *, transcript: str | None) -> tuple[dict[EmotionLabel, float], dict[str, float], str, str]: ...
```

```python
# src/dietary_guardian/agent/emotion/adapters/fusion_hf.py

class HFFusion(FusionPort):
    def __init__(self, model_id: str, device: str) -> None: ...
    def predict(self, *, text_scores, speech_scores, context) -> tuple[EmotionLabel, EmotionProductState, float, dict[EmotionLabel, float]]: ...
```

Update `InProcessEmotionRuntime` to raise `ValueError("fusion model not configured")` when `fusion_model_id` is missing.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -q tests/capabilities/test_emotion_service.py::test_runtime_raises_not_configured_when_fusion_missing`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/dietary_guardian/agent/emotion/adapters src/dietary_guardian/config/runtime.py src/dietary_guardian/agent/emotion/runtime.py tests/capabilities/test_emotion_service.py
git commit -m "feat: add HF emotion adapters and config"
```

---

## Chunk 4: API + Timeline Context + Docs

### Task 4: Update API and Timeline Context

**Files:**
- Modify: `apps/api/dietary_api/services/emotion_session.py`
- Modify: `apps/api/dietary_api/routers/emotions.py`
- Modify: `apps/api/dietary_api/schemas/core.py`
- Modify: `docs/api-emotions-contract.md`
- Test: `tests/api/test_api_emotions.py`

- [ ] **Step 1: Write failing test**

```python
# tests/api/test_api_emotions.py

def test_emotions_text_returns_full_trace() -> None:
    response = client.post("/api/v1/emotions/text", json={"text": "I feel good"})
    body = response.json()
    assert "text_branch" in body["observation"]
    assert "fusion" in body["observation"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest -q tests/api/test_api_emotions.py::test_emotions_text_returns_full_trace`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

Update `emotion_session.py` to map new `EmotionInferenceResult` into API schemas and append timeline events:

```python
context.event_timeline.append(
    event_type="emotion_observed",
    workflow_name="emotion_inference",
    request_id=request_id,
    correlation_id=correlation_id or str(uuid4()),
    user_id=str(session.get("user_id")),
    payload={"emotion": result.fusion.emotion_label, "product_state": result.fusion.product_state},
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -q tests/api/test_api_emotions.py::test_emotions_text_returns_full_trace`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/dietary_api/services/emotion_session.py apps/api/dietary_api/routers/emotions.py apps/api/dietary_api/schemas/core.py docs/api-emotions-contract.md tests/api/test_api_emotions.py
git commit -m "feat: update emotions api to full trace"
```

---

Plan complete and saved to `docs/superpowers/plans/2026-03-13-emotion-pipeline.md`. Ready to execute?
