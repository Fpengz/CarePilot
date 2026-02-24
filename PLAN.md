## Dietary Guardian v0.2 Plan: Real Image Upload, Role Tools, and Local Model Entries

### Summary
Implement three scoped upgrades in one coherent slice:
1. Real meal image input in Streamlit via file upload and camera capture.
2. Role-based tool surfaces for `patient`, `caregiver`, and `clinician` using a session role switcher.
3. Typed local-model entries (Ollama + vLLM) exposed in both config and UI selector for local testing.

Chosen defaults from your answers:
- Roles: 3 core roles.
- Image input: upload + camera.
- Local models: config + UI selector.
- Role gating: session role switcher (no auth yet).
- Image data handling: in-memory processing only; persist metadata/results only.

### Current-State Findings (Grounded)
- `src/app.py` currently uses a mock dish selectbox; no actual image upload/camera flow.
- `HawkerVisionModule.analyze_dish(image_input)` accepts `Any` but currently only uses text context.
- `provider_factory.py` already has `ollama` and `vllm` providers, but no structured profile entries for end-user selection.
- No role model or role-gated tool layout exists in UI/models.

### Implementation Scope
1. Add real image ingestion pipeline (UI + adapter layer).
2. Add role/tool domain models and role-gated UI tabs/actions.
3. Add typed local model profiles and selection wiring.
4. Add tests for upload flow, role gating, and local model selection behavior.
5. Update README usage for local model testing.

### Important API / Interface Changes
1. Add user role type to user model:
- File: `src/dietary_guardian/models/user.py`
- New enum/type: `UserRole = Literal["patient", "caregiver", "clinician"]`
- Extend `UserProfile` with `role: UserRole = "patient"`.

2. Add image-source and ingestion contract:
- File: `src/dietary_guardian/models/meal.py`
- Add `ImageInput` model:
  - `source: Literal["upload", "camera"]`
  - `filename: str | None`
  - `mime_type: str`
  - `content: bytes`
- Keep persistence policy: do not store `content` in app state/database; only process transiently.

3. Add role tool contracts:
- New file: `src/dietary_guardian/models/role_tools.py`
- Models:
  - `PatientToolState` (recent meals, reminder status)
  - `CaregiverToolState` (adherence summary, escalation flags)
  - `ClinicianToolState` (biomarker-grounded summary payload, export-ready text/json)

4. Add local model profile config:
- File: `src/dietary_guardian/config/runtime.py`
- Add models:
  - `LocalModelProfile` with fields `id`, `provider`, `model_name`, `base_url`, `api_key_env`, `enabled`.
  - `LocalModelSettings` with default profiles:
    - `ollama_llama3` => provider `ollama`, base URL `http://localhost:11434/v1`.
    - `vllm_qwen` => provider `vllm`, base URL `http://localhost:8000/v1`.
- Extend `AppConfig` with `local_models: LocalModelSettings`.

5. Provider selection interface:
- File: `src/dietary_guardian/agents/provider_factory.py`
- Add deterministic method:
  - `LLMFactory.from_profile(profile: LocalModelProfile) -> Model`
- Keep current `get_model(...)` for backward compatibility.
- Normalize local provider env fallback behavior for UI-selected profile.

### Detailed Build Plan

1. Image Upload/Capture UX in `src/app.py`
- Replace mock-only dish select with:
  - `st.file_uploader(..., type=["jpg","jpeg","png","webp"])`
  - `st.camera_input(...)`
- Add source picker or auto-source detection.
- Build `ImageInput` in memory from the selected artifact.
- Call `HawkerVisionModule.analyze_dish(image_input)` and render structured `VisionResult`.
- Add explicit “No image selected” guard and user-friendly failure messages.

2. Vision ingestion adapter in `src/dietary_guardian/agents/hawker_vision.py`
- Add helper to convert `ImageInput` to prompt-friendly context for current model capabilities.
- If model/mode cannot process binary image directly, run deterministic fallback:
  - Return clarification state with actionable retake instructions.
- Preserve current confidence thresholds and HPB fallback logic.
- Add tracing fields: source type, filename (if present), and latency.

3. Role-based tools in `src/app.py` + services
- Add sidebar session role switcher.
- Show role-specific sections:
  - Patient:
    - Upload/camera meal analysis.
    - Recent meal outcomes list.
    - After-meal reminder indicator (from current meal event state).
  - Caregiver:
    - Adherence overview cards.
    - High-risk meal alerts list.
  - Clinician:
    - Biomarker-grounded summary panel.
    - Export button for structured summary JSON/text.
- Keep shared core analysis pipeline across roles; only tools/views differ.

4. Role tool service scaffolding
- New file: `src/dietary_guardian/services/role_tools_service.py`
- Provide pure functions to compute role tool states from existing `MealEvent`/`MealState` and user context.
- Keep storage ephemeral via `st.session_state` for now.

5. Local model profile entries + UI selector
- In app sidebar:
  - Provider mode selector: `cloud` vs `local`.
  - If local: profile dropdown from config (`ollama_llama3`, `vllm_qwen`).
  - Optional override input for model name/base URL.
- Wire selection to `HawkerVisionModule(provider=..., model_name=...)` through profile mapping.
- Display active runtime badge (provider/model/base URL).

6. Documentation updates
- Update README with:
  - Local model setup examples for Ollama and vLLM.
  - How to switch profile in UI.
  - Clarify image privacy handling (in-memory only).

### Test Cases and Scenarios

1. Upload and camera ingestion
- New tests in `tests/test_app_upload_flow.py` and `tests/test_hawker_vision_image_input.py`.
- Cases:
  - Upload image accepted and passed to analysis adapter.
  - Camera image accepted and passed to analysis adapter.
  - No input selected yields clear UI guard behavior.
  - Unsupported mime/type handled safely.

2. Role gating correctness
- New tests in `tests/test_role_tools.py`.
- Cases:
  - Patient view shows only patient toolset.
  - Caregiver view shows adherence/alerts and hides clinician export.
  - Clinician view exposes summary export and hides caregiver-only actions.

3. Local model profile behavior
- New tests in `tests/test_local_model_profiles.py`.
- Cases:
  - Default profiles load from config.
  - Profile maps to correct provider/model/base URL.
  - Unknown profile falls back to safe test model path.
  - UI selection produces expected module initialization params.

4. Regression tests
- Keep existing `tests/test_hawker_vision.py`, `tests/test_safety.py`, `tests/test_virtual_patient.py` passing.
- Add one integration test: selected local profile + uploaded image returns `VisionResult` with safe failure/clarification path when model cannot process binary.

### Acceptance Criteria
- User can analyze meals using either uploaded image or camera capture from Streamlit.
- Three roles are selectable in-session and each sees only its tool bundle.
- Local model entries (Ollama + vLLM) are defined in typed config and selectable in UI.
- Image bytes are not persisted beyond request processing.
- Full suite passes: `uv run ruff check .`, `uv run ty check .`, `PYTHONPATH=src uv run pytest`.

### Assumptions and Defaults
- No full authentication in this iteration; role switching is session-based.
- No long-term image storage; only meal metadata/results persist in session state.
- Existing model SDK limitations for direct image input are handled via deterministic clarification fallback instead of brittle guesswork.
- Local profile defaults:
  - Ollama: `http://localhost:11434/v1`, model `llama3`.
  - vLLM: `http://localhost:8000/v1`, model `Qwen/Qwen2.5-7B-Instruct` (overridable).

