# Agent Modules — `src/dietary_guardian/agent/`

A complete reference for every module under the agent layer.

---

## Directory map

```
agent/
├── __init__.py
├── core/                        ← canonical agent contracts
│   ├── base.py                  ← BaseAgent, AgentContext, AgentResult
│   └── registry.py              ← AgentRegistry, build_default_agent_registry
├── runtime/                     ← inference plumbing
│   ├── inference_engine.py      ← InferenceEngine, strategy pattern
│   ├── inference_types.py       ← InferenceRequest/Response/Health, InferenceModality
│   ├── llm_factory.py           ← LLMFactory (multi-provider client builder)
│   ├── llm_routing.py           ← LLMCapabilityRouter (capability → runtime)
│   └── llm_types.py             ← ResolvedModelRuntime dataclass
├── dietary/
│   └── agent.py                 ← DietaryAgent (meal safety + LLM reasoning)
├── meal_analysis/
│   └── agent.py                 ← MealAnalysisAgent (vision → perception → record)
├── recommendation/
│   └── agent.py                 ← RecommendationAgent (daily plan synthesis)
├── emotion/
│   ├── agent.py                 ← EmotionAgent (text + speech emotion)
│   ├── schemas.py               ← EmotionTextAgentInput, EmotionSpeechAgentInput, EmotionAgentOutput
│   ├── audio_preprocessor.py
│   ├── config.py                ← EmotionRuntimeConfig
│   ├── engine.py                ← EmotionEngine (inference orchestrator)
│   ├── runtime.py               ← InProcessEmotionRuntime
│   ├── model_loader.py          ← EmotionModelLoader
│   ├── speech_classifier.py     ← SpeechEmotionClassifier
│   ├── text_classifier.py       ← TextEmotionClassifier
│   └── text_preprocessor.py
└── chat/                        ← SEA-LION conversational assistant
    ├── agent.py                 ← ChatAgent (history + streaming)
    ├── router.py                ← QueryRouter (LLM-based intent classification)
    ├── routes/
    │   ├── base.py              ← BaseRoute, RouteResult
    │   ├── drug_route.py        ← DrugRoute (medication queries)
    │   ├── food_route.py        ← FoodRoute (food/diet queries)
    │   └── code_route.py        ← CodeRoute (calculation via E2B sandbox)
    ├── audio_adapter.py         ← AudioAgent (Groq Whisper + MERaLiON transcription)
    ├── search_adapter.py        ← SearchAgent (DuckDuckGo wrapper)
    ├── memory.py                ← MemoryManager (short-term + SQLite long-term)
    ├── health_tracker.py        ← HealthTracker ([TRACK] metric parsing + charts)
    └── code_adapter.py          ← CodeAgent (E2B sandbox execution)
```

---

## `core/` — Agent contracts

### `core/base.py`

Defines the canonical contract all companion agents must satisfy.

| Symbol | Kind | Purpose |
|--------|------|---------|
| `AgentContext` | frozen dataclass | Request-scoped metadata (user_id, session_id, request_id, correlation_id, timestamp, metadata). Passed into every `run()` call. |
| `AgentResult[OutputT]` | generic dataclass | Standard result envelope: `success`, `agent_name`, `output`, `confidence`, `rationale`, `warnings`, `errors`, `raw`. All agents return this. |
| `BaseAgent[InputT, OutputT]` | abstract class | Abstract base. Subclasses must declare `name: str`, `input_schema`, `output_schema`, and implement `async run(input_data, context) → AgentResult`. |

**Pattern:** All four canonical agents (`DietaryAgent`, `MealAnalysisAgent`, `RecommendationAgent`, `EmotionAgent`) inherit from `BaseAgent` and return `AgentResult`. The chat-layer agents (`ChatAgent`, etc.) do **not** inherit from `BaseAgent` — they pre-date the canonical contract.

---

### `core/registry.py`

Static registry mapping agent IDs and workflow names to runtime contracts.

| Symbol | Purpose |
|--------|---------|
| `AgentRegistry` | Holds `AgentContract` and `WorkflowRuntimeContract` objects. Provides `list_agents()`, `list_workflow_contracts()`, `get_workflow_contract(name)`. |
| `build_default_agent_registry()` | Factory that registers all 5 canonical agents (`meal_analysis_agent`, `dietary_agent`, `recommendation_agent`, `emotion_agent`, `notification_agent`) and 3 workflow contracts (`MEAL_ANALYSIS`, `ALERT_ONLY`, `REPORT_PARSE`). |

**MEAL_ANALYSIS workflow steps:** `meal_analysis_agent → dietary_agent → notification_agent (timeline_emit)`

---

## `runtime/` — Inference plumbing

### `runtime/inference_engine.py`

Provider-agnostic inference execution engine. Sits between agents and the LLM client layer.

| Symbol | Purpose |
|--------|---------|
| `InferenceEngine` | Main entry point. Created with `provider`, `model_name`, optional `model`, `settings`, `capability`. Resolves a concrete `ProviderStrategy` on construction. |
| `CloudStrategy` | Wraps cloud models (Gemini, OpenAI). Uses `cloud_output_validation_retries` from `LLMSettings.inference`. |
| `LocalStrategy` | Wraps local models (Ollama, vLLM). Uses `local_output_validation_retries`. |
| `TestStrategy` | Wraps `TestModel`. Zero retries. |
| `ProviderStrategy` | Protocol: `supports(modality)`, `async run(request)`, `health()`. |

**`InferenceEngine.infer(request)`** calls `asyncio.wait_for(strategy.run(request), timeout=wall_clock_timeout_seconds)`. Raises `ValueError` if the provider doesn't support the requested modality (e.g., `TestModel` cannot handle `IMAGE`).

---

### `runtime/inference_types.py`

Pydantic models for the inference contract.

| Symbol | Purpose |
|--------|---------|
| `InferenceModality` | StrEnum: `TEXT`, `IMAGE`, `MIXED` |
| `InferenceRequest` | Input to `InferenceEngine.infer()`. Carries `request_id`, `modality`, `payload`, `output_schema` (Pydantic type), `system_prompt`, safety/runtime/trace context. |
| `InferenceResponse` | Output. Carries `structured_output`, `confidence`, `latency_ms`, `provider_metadata`, `raw_reference`. |
| `InferenceHealth` | Provider health snapshot: capability, provider, model, endpoint, `supports_modalities`, `healthy`. |
| `ModalityCapabilityProfile` | Full capability matrix with `expected_latency_ms` per modality. |
| `ProviderMetadata` | Flat metadata: capability, provider, model, endpoint. |

---

### `runtime/llm_factory.py` — `LLMFactory`

Static factory that builds concrete `pydantic_ai` model objects from settings.

| Method | Purpose |
|--------|---------|
| `get_model(provider, model_name, settings, capability)` | Main entry point. Resolves provider via `_resolve_runtime()`, then builds a `GoogleModel`, `OpenAIChatModel`, or `TestModel`. Falls back to `TestModel` on missing credentials. |
| `from_profile(profile: LocalModelProfile)` | Builds an `OpenAIChatModel` from a named local profile (Ollama/vLLM). |
| `_resolve_runtime(...)` | Reads `LLMSettings.capability_map` via `LLMCapabilityRouter` first; falls back to `settings.llm.provider` then explicit arg. Returns a `ResolvedModelRuntime`. |
| `_build_local_provider(base_url, api_key)` | Creates `AsyncOpenAI` client with local network config (timeout, retries) wrapped in `OpenAIProvider`. |
| `_build_openai_provider(api_key, base_url)` | Same pattern for OpenAI. |
| `describe_model_destination(model)` | Returns a human-readable string like `model=gemini-1.5-flash endpoint=default` for logging. |

**Supported providers:** `gemini`, `openai`, `ollama`, `vllm`, `codex`, `test`

---

### `runtime/llm_routing.py` — `LLMCapabilityRouter`

Maps a `LLMCapability` enum value to a `ResolvedModelRuntime` using `LLMSettings.capability_map`.

**Flow:** capability name → coerce to `LLMCapability` → look up in `capability_map` dict → fall back to `FALLBACK` entry if not found → resolve model name, base_url, api_key from settings views (`gemini`, `openai`, `local`).

---

### `runtime/llm_types.py`

| Symbol | Purpose |
|--------|---------|
| `ResolvedModelRuntime` | Frozen dataclass: `provider`, `model_name`, `capability`, `base_url`, `api_key`. Output of both `LLMFactory._resolve_runtime()` and `LLMCapabilityRouter.resolve()`. |

Also re-exports `LLMCapability`, `LLMCapabilityTarget`, `LocalModelProfile`, `ModelProvider` from `config.llm` for convenience.

---

## `dietary/` — Dietary reasoning agent

### `dietary/agent.py` — `DietaryAgent`

Canonical agent for meal safety checks and dietary advice generation.

**Persona:** "Uncle Guardian" — retired hawker, warm Singlish tone. Drops humor for critical safety violations.

**`run()` flow:**
1. Create `SafetyPort` (injected or default `SafetyEngine`).
2. Build `InferenceEngine` for `LLMCapability.DIETARY_REASONING`.
3. Call `safety.validate_meal(meal)` — collect warnings or raise `SafetyViolation`.
4. Build `InferenceRequest` with meal JSON as prompt + safety context.
5. Call `engine.infer(request)` → `AgentResponse` (analysis, advice, is_safe, warnings).
6. On `SafetyViolation`: return `success=False` with the violation message, skip LLM call.

**`AgentResponse`:** `analysis: str`, `advice: str`, `is_safe: bool`, `warnings: list[str]`

**Module-level singleton:** `dietary_agent = DietaryAgent()` — used by `process_meal_request()` convenience function.

**Logfire:** wrapped in `logfire.span("process_meal_request")`. `logfire.configure(send_to_logfire=False)` called at module level; `logfire_api = cast(Any, logfire)` suppresses type checker.

---

## `meal_analysis/` — Meal perception agent

### `meal_analysis/agent.py` — `MealAnalysisAgent`

Thin agent facade over `HawkerVisionModule`.

**`run()` flow:**
- If `persist_record=True`: calls `module.analyze_and_record(image, user_id)` → returns `(VisionResult, MealRecognitionRecord)`.
- If `persist_record=False`: calls `module.analyze_dish(image)` → returns `VisionResult` only.
- Wraps output in `AgentResult` with `confidence = float(vision_result.primary_state.confidence_score)`.

**Constructor args:** `provider`, `model_name`, `local_profile` (for Ollama), `food_store` (injectable canonical food lookup).

**Output schema:** `MealAnalysisAgentOutput(vision_result, meal_record | None)`

Also exposes `analyze_and_record()` as a direct method for callers that don't use the `run()` envelope.

---

## `recommendation/` — Recommendation agent

### `recommendation/agent.py` — `RecommendationAgent`

Pure facade over the `generate_daily_agent_recommendation` domain function. No LLM calls; the engine is deterministic.

**`generate(input_data, repository)`** — synchronous. Calls `generate_daily_agent_recommendation(...)` from `features/recommendations/domain/engine.py`.

**`run(input_data, context)`** — async wrapper. Reads `repository` from `context.metadata["repository"]`. Computes mean confidence across recommendation cards.

**Input schema:** `RecommendationAgentInput` (user_id, health_profile, user_profile, meal_history, clinical_snapshot)
**Output schema:** `RecommendationAgentOutput(recommendation: DailyRecommendationBundle)`

---

## `emotion/` — Emotion inference agent

### `emotion/agent.py` — `EmotionAgent`

Canonical agent facade for text and speech emotion inference. **Not** a `BaseAgent` subclass in the strict sense — it accepts a union input type `EmotionTextAgentInput | EmotionSpeechAgentInput`.

**Constructor:** requires explicit injection of `runtime: EmotionInferencePort`, `inference_enabled`, `speech_enabled`, `request_timeout_seconds`.

**`run()` flow:**
- Raises `EmotionAgentDisabledError` if `inference_enabled=False`.
- Text input → calls `infer_text_emotion(runtime, text, language, timeout)`.
- Speech input → raises `EmotionSpeechDisabledError` if `speech_enabled=False`; otherwise calls `infer_speech_emotion(runtime, audio_bytes, ...)`.
- Wraps result in `AgentResult[EmotionAgentOutput]`.

---

### `emotion/schemas.py`

Pure input/output contracts for the emotion agent. No infrastructure dependencies.

| Schema | Fields |
|--------|--------|
| `EmotionTextAgentInput` | `text: str`, `language: str \| None` |
| `EmotionSpeechAgentInput` | `audio_bytes: bytes`, `filename`, `content_type`, `transcription`, `language` |
| `EmotionAgentOutput` | `inference: EmotionInferenceResult` |

---

### `emotion/` — Emotion runtime infrastructure

| Module | Purpose |
|--------|---------|
| `config.py` — `EmotionRuntimeConfig` | Pydantic settings for model names, thresholds, speech weight, timeout. |
| `model_loader.py` — `EmotionModelLoader` | Loads HuggingFace `pipeline` for text emotion (`j-hartmann/emotion-english-distilroberta-base`). Lazy-loads on first use. |
| `text_preprocessor.py` | Normalizes text: strips whitespace, lowercase, truncates to token limit. |
| `text_classifier.py` — `TextEmotionClassifier` | Runs the HF text classification pipeline. Maps raw labels (`anger`, `disgust`, `fear`, `joy`, …) to unified `EmotionLabel` enum. |
| `audio_preprocessor.py` | Decodes raw audio bytes → `float32` numpy array at target sample rate. |
| `speech_classifier.py` — `SpeechEmotionClassifier` | Audio heuristic (energy + ZCR) as placeholder for MERaLiON speech emotion. Returns a score and label with a confidence band. |
| `engine.py` — `EmotionEngine` | Orchestrates text + speech classifiers. Fuses speech (60%) + text (40%) for audio input; text-only path for text input. Returns `EmotionInferenceResult`. |
| `runtime.py` | `InProcessEmotionRuntime` — implements `EmotionInferencePort` using the local `EmotionEngine`. Used as the default runtime in production. |

---

## `meal_analysis/` — Hawker food vision

### `meal_analysis/vision_module.py` — `HawkerVisionModule`

Meal image perception and normalization module. Used by `MealAnalysisAgent`.

**Constructor:** `provider`, `model_name`, `local_profile` (for Ollama), `food_store`. Builds `InferenceEngine` and a lazy `_LazyMealPerceptionAgent` (deferred `pydantic_ai.Agent` construction to avoid serialization issues).

**`analyze_dish(image_input, user_id, ...)` flow:**
1. Prepare image prompt (base64 or URL).
2. Call `InferenceEngine.infer()` for `IMAGE` or `MIXED` modality → `MealPerception` structured output.
3. Normalize → `VisionResult` with `primary_state`, `alternative_states`, nutrition, ingredients, GI level.
4. Log slow inference warnings (> 10 s).
5. Return `VisionResult`.

**`analyze_and_record(image_input, user_id, ...)` flow:**
1. Calls `analyze_dish()`.
2. Calls `build_meal_record(user_id, vision_result)` → `MealRecognitionRecord`.
3. Returns `(VisionResult, MealRecognitionRecord)`.

**`_SeededFoodStore`:** in-memory food catalog built from `build_default_canonical_food_records()`. Used when no persistent store is injected (e.g., during testing or first-run before DB init).

---

## `chat/` — SEA-LION conversational assistant

The `chat/` sub-package is the integration point for Ervin's SEA-LION health chatbot. These modules do **not** inherit from `BaseAgent`, but they now follow the same dependency-injection and runtime wiring conventions as other agents.

### `chat/agent.py` — `ChatAgent`

Manages conversation history and calls the SEA-LION OpenAI-compatible LLM endpoint.

- Constructor: `client: OpenAI`, `model_id`, `router: QueryRouter | None`, `session_id`.
- `stream_async(message, async_client, model_id)` → `AsyncIterator[str]`: streams SSE chunks via `AsyncOpenAI`.
- Internally uses `MemoryManager` for history and `QueryRouter` for context enrichment.

---

### `chat/router.py` — `QueryRouter`

LLM-based intent classifier. Routes user queries to one of four handlers.

**Labels:** `drug`, `food`, `code`, `general`

**Flow:** calls SEA-LION with a classification prompt → receives a single label → dispatches to `DrugRoute.enrich()`, `FoodRoute.enrich()`, `CodeRoute.enrich()`, or returns no enrichment for `general`.

Receives `OpenAI` client + model ids via dependency injection.

---

### `chat/routes/base.py`

| Symbol | Purpose |
|--------|---------|
| `RouteResult` | Dataclass: `route_name: str`, `context: str \| None`, `metadata: dict`. Returned by all routes. |
| `BaseRoute` | Abstract base with `enrich(text: str) → RouteResult`. All route handlers extend this. |

---

### `chat/routes/drug_route.py` — `DrugRoute`

Handles medication queries (diabetes, hypertension, cardiovascular drugs).

- Calls SEA-LION to compress the user's question into a 3–6 word search phrase.
- Runs a DuckDuckGo search via `SearchAgent` biased toward Singapore clinical reference sites.
- Distills the top results into a concise medication fact summary using SEA-LION.
- Returns `RouteResult(route_name="drug", context=<summary>)`.

Uses the injected `OpenAI` client.

---

### `chat/routes/food_route.py` — `FoodRoute`

Handles food, diet, and nutrition advisory queries with Singapore hawker context.

Same pipeline as `DrugRoute`: compress → DuckDuckGo search → distill → return context. Search biased toward Singapore dietary guidelines and hawker food databases.

---

### `chat/routes/code_route.py` — `CodeRoute`

Handles calculation/computation queries via a secure sandbox.

1. LLM translates the natural-language question into a Python script.
2. `CodeAgent` executes the script in an E2B cloud sandbox.
3. Returns the sandbox stdout as enriched context for the final LLM reply.

Uses injected `OpenAI` + `CodeAgent` instances.

---

### Emotion in chat

Chat uses the canonical `agent/emotion/` runtime via API wiring; there is no separate chat-layer emotion agent.

---

### `chat/audio_adapter.py` — `AudioAgent`

Transcribes audio input into text.

| Backend | When used |
|---------|-----------|
| Groq Whisper | Cloud-based, fast. Default. Uses injected Groq API key. |
| MERaLiON | Local model, Singapore-English focused. Requires `load_model()` call first. |

---

### `chat/search_adapter.py` — `SearchAgent`

Thin DuckDuckGo wrapper. Returns a list of `SearchResult(title, url, snippet)`. Used by all three route handlers. No routing logic here.

---

### `chat/memory.py` — `MemoryManager`

Hybrid short-term + long-term memory for `ChatAgent`.

| Store | What |
|-------|------|
| SQLite (`data/runtime/chat_memory.db`) | All messages persisted permanently. |
| In-memory list | Last `SHORT_TERM_SIZE` messages for LLM prompt context. |
| Rolling summary | LLM-generated summary of messages before the short-term window, updated every `SHORT_TERM_SIZE` new messages. |

`build_prompt_context()` returns `{"rolling_summary": str | None, "short_term": list[dict]}` injected into the ChatAgent prompt.

---

### `chat/health_tracker.py` — `HealthTracker`

Parses `[TRACK]` prefixed messages from `chat_memory.db` and generates line-chart visualizations.

- Users send messages like `[TRACK] fasting blood glucose 7.2 mmol/L`.
- LLM extracts `metric_type`, `value`, `unit` from each message.
- Results cached in `health_parsed_metrics` table (no message re-parsed twice).
- `generate_charts(metric_filter, start_date, end_date)` → `matplotlib` figure with one subplot per metric type.

---

### `chat/code_adapter.py` — `CodeAgent`

Executes Python code in a secure E2B cloud sandbox (`e2b-code-interpreter`).

- `run(code: str)` → stdout as string.
- Uses injected E2B API key at runtime (wired in API deps).

---

## Design notes and known issues

### What's consistent (canonical agents)
- `DietaryAgent`, `MealAnalysisAgent`, `RecommendationAgent`, `EmotionAgent` all inherit `BaseAgent`, declare `name`/`input_schema`/`output_schema`, return `AgentResult`.
- All canonical agents use `InferenceEngine` + `LLMFactory` from `runtime/`.
- All accept dependency injection via constructor (`safety_port`, `runtime`, `food_store`, etc.).

### What's inconsistent (chat agents)
- `ChatAgent`, `QueryRouter`, `DrugRoute`, `FoodRoute`, `CodeRoute` do **not** inherit `BaseAgent`.
- Routes use injected `OpenAI` clients and runtime settings; no env reads in route bodies.
- Settings are centralized in API wiring for `SEALION_API`, `CHAT_MODEL_ID`, `REASONING_MODEL_ID`, `GROQ_API_KEY`, `E2B_API_KEY`.

### Refactor opportunities (tracked in REFACTOR_PLAN.md)
1. Wrap `ChatAgent`/routes in a `BaseAgent` subclass or at minimum an `LLMSettings`-aware factory.
2. Keep route classes accepting injected `OpenAI` clients via constructor (done).
3. Keep chat emotion using the canonical `agent/emotion/` runtime (done).
4. `dietary/agent.py` logfire cast workaround (`cast(Any, logfire)`) should be removed once logfire typing is resolved.
5. `AgentRegistry` currently stores only static `AgentContract` metadata — it does not hold live agent instances. Future: expose `get_agent(agent_id) → BaseAgent` for dynamic dispatch.
