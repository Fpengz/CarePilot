# Agent Modules — `src/care_pilot/agent/`

A complete reference for every module under the agent layer.

## Standards (architecture guardrails)

- **Inference agents:** standardize on `pydantic_ai` via the agent runtime (`agent/runtime/*`). Feature/workflow/API code must not instantiate `pydantic_ai.Agent` directly.
- **Workflows:** standardize on **LangGraph** for declared multi-step product journeys (typed workflow state + explicit steps).
- **Domain logic:** rules/persistence/scheduling remain deterministic in `features/**/domain`.

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
│   ├── ports.py                 ← ASR/Text/Speech/Fusion ports
│   ├── pipeline.py              ← EmotionPipeline (ASR → branches → fusion)
│   ├── adapters/
│   │   ├── asr_meralion.py       ← MERaLiON ASR adapter
│   │   ├── text_hf.py            ← HF text emotion adapter
│   │   ├── speech_hf.py          ← HF speech emotion adapter
│   │   └── fusion_hf.py          ← HF fusion adapter
│   ├── engine.py                ← Legacy heuristic engine
│   ├── runtime.py               ← InProcessEmotionRuntime (pipeline-backed)
│   ├── model_loader.py          ← Legacy model loader
│   ├── speech_classifier.py     ← Legacy speech classifier
│   ├── text_classifier.py       ← Legacy text classifier
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

**Pattern:** All canonical agents (`DietaryAgent`, `MealAnalysisAgent`, `RecommendationAgent`, `EmotionAgent`, and `ChatAgent`) inherit from `BaseAgent` and return `AgentResult`. The chat subsystem exposes streaming helpers, but the core entrypoint is now a typed `ChatAgent.run()`.

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

### `runtime/chat_runtime.py`

SEA-LION chat runtime adapters used by the chat subsystem.

| Symbol | Purpose |
|--------|---------|
| `ChatStreamRuntime` | Owns the SEA-LION `AsyncOpenAI` client and streams tokens with retry/backoff. |
| `build_chat_inference_engine(...)` | Builds an `InferenceEngine` wired to SEA-LION settings for structured chat tasks. |

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

**Supported providers:** `gemini`, `openai`, `qwen`, `ollama`, `vllm`, `codex`, `test`

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
| `EmotionTextAgentInput` | `text: str`, `language: str \| None`, `context: EmotionContextFeatures \| None` |
| `EmotionSpeechAgentInput` | `audio_bytes: bytes`, `filename`, `content_type`, `transcription`, `language`, `context: EmotionContextFeatures \| None` |
| `EmotionAgentOutput` | `inference: EmotionInferenceResult` |

---

### `emotion/` — Emotion runtime infrastructure

| Module | Purpose |
|--------|---------|
| `config.py` — `EmotionRuntimeConfig` | Runtime settings for model IDs, device, history window, and source commit. |
| `ports.py` | Protocols for ASR, text emotion, speech emotion, and fusion adapters. |
| `pipeline.py` — `EmotionPipeline` | Orchestrates ASR → text/speech branches → context → fusion; emits full-trace `EmotionInferenceResult`. |
| `audio_preprocessor.py` | Validates raw audio bytes and content type. |
| `adapters/asr_meralion.py` | MERaLiON ASR adapter (audio bytes → transcript). |
| `adapters/text_hf.py` | HF text emotion adapter using `pipeline("text-classification")`. |
| `adapters/speech_hf.py` | HF speech emotion adapter using `pipeline("audio-classification")`. |
| `adapters/fusion_hf.py` | HF fusion adapter that consumes structured features and returns `emotion_label` + `product_state`. |
| `engine.py` — `EmotionEngine` | Legacy heuristic engine retained for fallback/testing only. |
| `runtime.py` | `InProcessEmotionRuntime` — implements `EmotionInferencePort` using `EmotionPipeline`. |

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

The `chat/` sub-package is the integration point for the SEA-LION health chatbot. Chat now follows the canonical agent contract and exposes a typed `ChatAgent.run()` entrypoint, plus a streaming helper for SSE.

### `chat/agent.py` — `ChatAgent`

Manages conversation history and calls the SEA-LION OpenAI-compatible LLM endpoint.

- Constructor: `stream_runtime`, `router: QueryRouter | None`, `memory: MemoryManager`, `model_id`.
- `run(input: ChatInput, context)` → `AgentResult[ChatOutput]`: non-streaming agent contract.
- `stream(user_message, emotion_context)` → `AsyncIterator[str]`: yields SSE envelopes `{"event": "...", "data": {...}}`.
- Internally uses `MemoryManager` for history and `QueryRouter` for context enrichment.

### `chat/schemas.py`

Typed contracts for `ChatInput`, `ChatOutput`, route labels, and SSE event envelopes.

---

### `chat/router.py` — `QueryRouter`

LLM-based intent classifier. Routes user queries to one of four handlers.

**Labels:** `drug`, `food`, `code`, `general`

**Flow:** calls SEA-LION with a classification prompt → receives a single label → dispatches to `DrugRoute.enrich()`, `FoodRoute.enrich()`, `CodeRoute.enrich()`, or returns no enrichment for `general`.

Receives a chat `InferenceEngine` via dependency injection.

---

### `chat/routes/base.py`

| Symbol | Purpose |
|--------|---------|
| `RouteResult` | Dataclass: `route_name: ChatRouteLabel`, `context: str \| None`, `metadata: dict`. Returned by all routes. |
| `BaseRoute` | Abstract base with `enrich(text: str) → RouteResult`. All route handlers extend this. |

---

### `chat/routes/drug_route.py` — `DrugRoute`

Handles medication queries (diabetes, hypertension, cardiovascular drugs).

- Calls SEA-LION to compress the user's question into a 3–6 word search phrase.
- Runs a DuckDuckGo search via `SearchAgent` biased toward Singapore clinical reference sites.
- Distills the top results into a concise medication fact summary using SEA-LION.
- Returns `RouteResult(route_name="drug", context=<summary>)`.

Uses the injected chat `InferenceEngine`.

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

Uses injected `InferenceEngine` + `CodeAgent` instances.

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
- Chat now follows the `BaseAgent` contract, but streaming uses a bespoke SSE helper rather than `InferenceEngine`.
- Route enrichment is synchronous and uses `asyncio.run` for inference, which is acceptable but could be made fully async in the future.
- Settings remain centralized in API wiring for `SEALION_API`, `CHAT_MODEL_ID`, `REASONING_MODEL_ID`, `GROQ_API_KEY`, `E2B_API_KEY`.

### Refactor opportunities
1. Move sync route enrichment to an async interface to avoid `asyncio.run`.
2. Keep chat emotion using the canonical `agent/emotion/` runtime (done).
3. `dietary/agent.py` logfire cast workaround (`cast(Any, logfire)`) should be removed once logfire typing is resolved.
4. `AgentRegistry` currently stores only static `AgentContract` metadata — it does not hold live agent instances. Future: expose `get_agent(agent_id) → BaseAgent` for dynamic dispatch.
