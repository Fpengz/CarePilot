# CarePilot Roadmap: Multi-Modal & Memory Layers

## 1. Multi-Modal Ingestion (PDF/Voice)

### PDF Lab Result Processing
- **Goal**: Automatically update clinical profile from lab PDFs.
- **Workflow**:
    1.  User Uploads PDF -> `API /api/v1/clinical/ingest`.
    2.  `IngestionAgent` (Gemini Flash with `multimodal` capability) parses OCR.
    3.  Extract Key Biomarkers: HbA1c, LDL-C, SBP, DBP, BMI.
    4.  Update `BiomarkerReadingRepository`.
    5.  Emit `ClinicalUpdateEvent` -> `CarePlanAgent` updates advice.

### Voice Fusion (Speech + Text)
- **Goal**: Extract emotional context from *how* someone speaks.
- **Workflow**:
    1.  User Records Voice -> `stream_audio_events`.
    2.  Acoustic Feature Extraction (Pitch, Rate, Intensity) via `InferenceAgent`.
    3.  Fuse Text Emotion (Whisper -> Roberta) + Acoustic Emotion (Wav2Vec2).
    4.  Update Blackboard with `FusedEmotion`.

## 2. Memory Layer Refinements (Mem0)

### Temporal Working Memory
- **Goal**: Cache small fragments for immediate interaction but decay them quickly.
- **Strategy**: Implement `ShortTermMemoryStore` in `CacheStore` with 30-minute TTL.

### Semantic Fact Management
- **Goal**: Let users manage what the AI "knows."
- **Actions**:
    - `api/v1/memory/list`: Returns list of facts extracted by Mem0.
    - `api/v1/memory/delete`: Allows user to "Forget" specific facts.
- **Optimization**: Use Semantic Similarity to prevent redundant fact storage (e.g., "User likes tea" vs "User enjoys tea").

## 3. Persistent Snapshot Projections
- **Goal**: Move snapshot generation *off* the request path.
- **Strategy**: 
    - When any domain repository updates (Meal, Med, BP), trigger an async task.
    - `SnapshotProjector` recomputes the relevant section of the JSON snapshot.
    - Store result in `eventing_store.snapshot_sections` table.
    - `ChatOrchestrator` only performs 1-2 indexed reads.
