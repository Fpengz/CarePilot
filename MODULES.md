# Module Reference — SEA-LION Health Assistant

A detailed explanation of every module, file, and directory in this repository.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Root-Level Files](#root-level-files)
3. [`agents/` — Core Agent Logic](#agents--core-agent-logic)
4. [`backend/` — FastAPI Application](#backend--fastapi-application)
5. [`routes/` — Query Routing & Enrichment](#routes--query-routing--enrichment)
6. [`ingestion/` — Data Ingestion & Retrieval](#ingestion--data-ingestion--retrieval)
7. [`frontend/` — Next.js UI](#frontend--nextjs-ui)
8. [`data/` — Static Knowledge Base](#data--static-knowledge-base)
9. [Runtime Stores (`vectorstore/`)](#runtime-stores-vectorstore)
10. [Data Flow Diagrams](#data-flow-diagrams)

---

## Project Overview

SEA-LION Health Assistant is a Singapore-focused conversational health assistant for patients managing chronic diseases (diabetes, hypertension, cardiovascular disease). It combines a **FastAPI** backend and a **Next.js** frontend with several AI capabilities:

| Layer | Technology |
|---|---|
| LLM | SEA-LION v4 (`aisingapore/Gemma-SEA-LION-v4-27B-IT`) via OpenAI-compatible API |
| Reasoning | SEA-LION v3.5 70B Reasoning (`aisingapore/Llama-SEA-LION-v3.5-70B-R`) |
| Audio transcription | Groq Whisper (`whisper-large-v3`) — cloud; MERaLiON 2-3B — local optional |
| Emotion detection | `j-hartmann/emotion-english-distilroberta-base` (HuggingFace, ~330 MB) |
| Vector database | ChromaDB (persistent, cosine similarity) |
| Relational storage | SQLite (chat memory, health metrics, medications) |
| Secure execution | E2B cloud Python sandbox |
| Backend | FastAPI + Uvicorn, async SSE streaming |
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Recharts |

---

## Root-Level Files

### `main.py` — Legacy Gradio UI

An older Gradio-based chat interface that predates the Next.js frontend. It directly instantiates `ChatAgent`, `AudioAgent`, `HealthTracker`, `UserMedDB`, and the query router, then assembles a multi-tab Gradio UI (Chat, Medications, Dashboard).

**Status:** Superseded by the `backend/` + `frontend/` stack. Retained for historical reference but **not used** in normal operation.

---

### `requirements.txt` — Python Dependencies

Lists all Python dependencies for the backend. Key groups:

| Group | Notable packages |
|---|---|
| API / web | `fastapi`, `uvicorn`, `openai`, `groq` |
| ML / embeddings | `transformers`, `torch`, `sentence-transformers`, `onnxruntime` |
| Audio | `faster-whisper`, `librosa`, `soundfile` |
| Vector DB | `chromadb` |
| Sandbox | `e2b-code-interpreter` |
| Utilities | `pydantic`, `python-dotenv`, `duckduckgo-search` (ddgs) |

Install with:
```bash
pip install -r requirements.txt
```

---

### `README.md` — Project Documentation

Top-level setup guide covering features, folder structure, prerequisites, environment variable configuration, startup instructions, API endpoint reference, health tracking syntax, emotion detection, E2B sandbox, and database schemas.

---

### `todos.md` — Development Task List

Internal task tracker with completed and pending items. Completed work includes: food tool (local RAG + web), drug tool (web search), medication UI & DB, long/short-term memory, tracked numbers dashboard, and MCP Python sandbox. Pending work includes food data gaps, drug timing integration, and a PDF route.

---

## `agents/` — Core Agent Logic

All agents are pure Python classes with **zero FastAPI dependencies**, making them portable and independently testable. They are instantiated once in `backend/deps.py` and shared across all requests.

---

### `agents/chat_agent.py` — Conversation Manager

**Class:** `ChatAgent`

The central orchestrator for every user interaction. It owns the conversation memory, calls the query router, builds the LLM prompt, streams the response, and persists the reply.

**Constructor parameters:**

| Parameter | Default | Description |
|---|---|---|
| `api_key` | `$SEALION_API` | SEA-LION API key |
| `base_url` | `https://api.sea-lion.ai/v1` | OpenAI-compatible endpoint |
| `model_id` | `$CHAT_MODEL_ID` | LLM model identifier |
| `router` | `None` | `QueryRouter` instance for enrichment |
| `session_id` | `"default"` | Conversation session identifier |

**Key methods:**

| Method | Description |
|---|---|
| `build_api_messages(extra_context, emotion_context)` | Assembles the full message list for the LLM API call. Merges the system prompt, optional emotion context, rolling summary, and short-term window header into a single `system` message (the SEA-LION endpoint rejects consecutive system roles). Appends the short-term `user`/`assistant` turns. When `extra_context` is provided (from a route), injects it into the last user message so the LLM answers with access to the retrieved data. |
| `route_async(user_message)` | Runs the synchronous `QueryRouter.route()` in a thread-pool executor so it does not block the async event loop. Returns a context string or `None`. |
| `stream_async(user_message, async_client, model_id, emotion_context)` | Full streaming pipeline: persist message → check `[TRACK]` prefix → route → build prompt → stream LLM tokens via SSE → persist reply. Yields `data: {"text": "token"}` chunks, then `data: {"done": true}`. |
| `clear_history()` | Deletes all `chat_messages` and `chat_summaries` rows for the session from SQLite, and resets in-memory state. |

**`[TRACK]` fast-path:** If the message starts with `[TRACK]` (case-insensitive), the agent immediately stores `"Tracked."` as the assistant reply and returns — no LLM call is made. The raw `[TRACK]` message is used by `HealthTracker` later.

**System prompt:**
> "You are SEA-LION, a helpful health assistant specialised in Singapore's food, medications, and chronic-disease management…"

---

### `agents/audio_agent.py` — Audio Transcription

**Class:** `AudioAgent`

Converts raw audio into text. Supports two backends:

| Backend | Method | When to use |
|---|---|---|
| **Groq Whisper** (default) | `transcribe_bytes(raw_bytes, filename)` | FastAPI file upload (webm/mp3/wav/ogg) — no GPU needed, very fast |
| **Groq Whisper** (numpy) | `transcribe_groq(audio_input)` | Gradio-style `(sample_rate, np.ndarray)` input |
| **MERaLiON 2-3B** (local) | `transcribe(audio_input)` | Local inference on Apple MPS or CPU, Singapore-English focus — call `load_model()` first |

**Key behaviour:**
- Resamples audio to 16 kHz when necessary (using `librosa.resample`).
- Passes `prompt="Singlish, Singapore English"` to Groq to bias transcription toward local pronunciation.
- MERaLiON uses a chat-template prompt: `"Please transcribe this speech."`.
- Returns a plain text string (not a conversational reply).

---

### `agents/emotion_agent.py` — Emotion Classifier

**Class:** `EmotionAgent` (Singleton, thread-safe via `threading.Lock`)

Detects the user's emotional state from text or transcribed audio using `j-hartmann/emotion-english-distilroberta-base`. The model is **lazy-loaded** on first use (~330 MB, downloaded from HuggingFace).

**Dataclass `EmotionResult`:**

| Field | Type | Description |
|---|---|---|
| `emotion` | `str` | Unified label: `happy`, `sad`, `angry`, `frustrated`, `fearful`, `neutral`, `confused` |
| `score` | `float` | Top-label confidence (0.0–1.0) |
| `input_type` | `str` | `"text"` or `"speech"` |
| `all_scores` | `list[dict]` | Full distribution across all labels |
| `transcription` | `str \| None` | Set when input is audio |

**Raw → unified label mapping** (`_TEXT_LABEL_MAP`):

| HuggingFace raw | Unified |
|---|---|
| `anger` | `angry` |
| `disgust` | `frustrated` |
| `fear` | `fearful` |
| `joy` | `happy` |
| `neutral` | `neutral` |
| `sadness` | `sad` |
| `surprise` | `confused` |

**Key methods:**

| Method | Description |
|---|---|
| `analyze_text(text)` | Runs DistilRoBERTa on the raw message. Falls back to `neutral` if confidence < 0.30. |
| `analyze_audio(raw_bytes, filename, transcription)` | Runs DistilRoBERTa on the Groq transcription. Returns `neutral` if no transcription provided. |
| `to_context_str(result)` *(static)* | Formats the result as a prompt snippet: `"[Emotional context] The user appears to be feeling **sad** (confidence 87%)…"` — injected into the LLM system prompt. |

**Singleton pattern:** Only one copy of the model weights lives in memory regardless of how many times `EmotionAgent()` is called. The `_instance` class variable and `_init_lock` ensure thread-safe instantiation.

**MERaLiON speech-emotion block:** A full MERaLiON-AudioLLM paralinguistic speech-emotion path is present in the file but commented out due to memory cost. The audio path currently runs DistilRoBERTa on the Groq transcription directly.

---

### `agents/code_agent.py` — Secure Python Sandbox

**Class:** `CodeAgent`

Executes arbitrary Python snippets inside an [E2B](https://e2b.dev/) cloud sandbox. Used by `CodeRoute` for calculation queries and by `dashboard.py` for computing metric trends.

**Constructor:** Reads `E2B_API_KEY` from environment at import time. Raises `EnvironmentError` if the key is missing.

**`run(code, timeout=60)` method:**

1. Creates a fresh `Sandbox` via `Sandbox.create(timeout=timeout)`.
2. Executes `code` with `sandbox.run_code(code)`.
3. Returns `stdout` if present; falls back to the last `execution.results` value.
4. Returns a formatted error string on any execution or sandbox failure.
5. Always calls `sandbox.kill()` in the `finally` block to release resources.

**Security:** Code never runs on the local host — E2B provides an isolated, ephemeral container. Each call spins up a new sandbox.

---

### `agents/health_tracker.py` — Health Metric Parser & Chart Builder

**Class:** `HealthTracker`

Reads `[TRACK]` messages from SQLite, extracts numeric metrics using the LLM (with DB caching), and produces chart-ready data for the dashboard.

**Constructor parameters:** `session_id`, `client` (sync OpenAI), `model_id`, `db_path` (defaults to `vectorstore/chat_memory.db`).

**Public methods:**

| Method | Returns | Description |
|---|---|---|
| `build_chart(start_date, end_date)` | `matplotlib.Figure` | Renders one subplot per metric type as line charts with annotations. Used by the Gradio legacy UI. |
| `get_raw_entries(start_date, end_date)` | `list[dict]` | Raw `[TRACK]` messages in the date window (for table display). |
| `get_chart_data(start_date, end_date)` | `dict` | JSON-serialisable metric data grouped by type, ready for Recharts. Shape: `{"metrics": {"weight": {"label", "unit", "data": [{"date", "value"}]}}}`. |

**LLM parse prompt** (`_PARSE_PROMPT`): Asks the LLM to return a JSON array of `{metric_type, value, unit, label}` objects. Blood pressure `"140/90"` emits **two** entries (systolic + diastolic). Results cached in `health_parsed_metrics` table — each `(message_id, metric_type)` pair is only parsed once.

**Supported `metric_type` values:**

`weight` · `blood_pressure_systolic` · `blood_pressure_diastolic` · `blood_glucose` · `hba1c` · `heart_rate` · `cholesterol_total` · `cholesterol_ldl` · `cholesterol_hdl` · `symptom_severity`

**SQLite table created:** `health_parsed_metrics` — columns: `message_id`, `session_id`, `metric_type`, `value`, `unit`, `label`, `recorded_at`. Has a `UNIQUE (message_id, metric_type)` constraint to prevent duplicate caching.

---

### `agents/memory_manager.py` — Conversation Memory

**Class:** `MemoryManager`

Provides a two-tier memory system: a short-term in-memory window for the LLM prompt, and a persistent rolling summary of older messages stored in SQLite.

**Constants:**

| Constant | Value | Meaning |
|---|---|---|
| `SHORT_TERM_SIZE` | `3` | Number of most-recent messages kept in the prompt window |
| `SUMMARIZE_EVERY` | `3` | Trigger a new summary after this many messages leave the window |

**Public methods:**

| Method | Description |
|---|---|
| `add_message(role, content)` | Appends to in-memory list, persists to `chat_messages`, then calls `_maybe_update_summary()`. |
| `build_prompt_context()` | Returns `{"rolling_summary": str \| None, "short_term": list[dict]}` for use by `ChatAgent`. |
| `all_messages()` | Returns every message (for history display). |
| `rolling_summary` *(property)* | Current rolling summary text. |

**Summarisation trigger (`_maybe_update_summary`):** When `len(messages) - SHORT_TERM_SIZE - summarized_up_to >= SUMMARIZE_EVERY`, the LLM is called to merge the newly-eligible batch into the rolling summary. The summary is saved to the `chat_summaries` table.

**SQLite tables used:**

| Table | Purpose |
|---|---|
| `chat_messages` | Full message history: `session_id`, `role`, `content`, `created_at` |
| `chat_summaries` | Rolling summary per session: `summary`, `summarized_up_to`, `updated_at` |

**Summary prompt (`_SUMMARY_PROMPT`):** Instructs the LLM to produce a concise third-person summary (`"The user asked… The assistant explained…"`) of a batch of messages merged with the existing summary.

---

### `agents/search_agent.py` — Web Search

**Class:** `SearchAgent`  
**NamedTuple:** `SearchResult(title, url, body)`

A thin wrapper around [DuckDuckGo Search](https://pypi.org/project/duckduckgo-search/) (`ddgs`). Called by `DrugRoute` and `FoodRoute`.

**`search(query)` method:**
- Uses `region="sg-en"` to bias results toward Singapore sources.
- Returns up to `max_results` (default 3) `SearchResult` objects.
- Swallows all exceptions (network errors, rate limits) and returns an empty list — routes gracefully degrade to plain LLM responses.

---

## `backend/` — FastAPI Application

### `backend/main.py` — Application Entry Point

Creates the FastAPI app, registers CORS middleware, and mounts all routers.

**CORS configuration:** Allows `http://localhost:3000` and `http://127.0.0.1:3000` (the Next.js dev server). All methods and headers are permitted.

**Registered routers:**
- `chat.router` → `/api/chat`
- `medications.router` → `/api/medications`
- `dashboard.router` → `/api/dashboard`
- `emotion_router.router` → `/api/emotion`

**Health check:** `GET /health` → `{"status": "ok"}`

**Path fix:** Inserts the project root into `sys.path` at startup so all top-level packages (`agents/`, `routes/`, etc.) are importable regardless of the working directory.

---

### `backend/deps.py` — Singleton Initialisation

Instantiates every agent and client once at backend startup and exports them for use across all routers.

**Exported singletons:**

| Name | Type | Description |
|---|---|---|
| `chat_agent` | `ChatAgent` | Manages conversation, memory, and LLM streaming |
| `audio_agent` | `AudioAgent` | Audio transcription via Groq or MERaLiON |
| `emotion_agent` | `EmotionAgent` | DistilRoBERTa emotion classifier (singleton) |
| `async_client` | `AsyncOpenAI` | Async client for SSE streaming (same credentials as `chat_agent`) |
| `health_tracker` | `HealthTracker` | `[TRACK]` metric parser & chart data provider |
| `user_med_db` | `UserMedDB` | SQLite-backed medication schedule store |
| `prescription_parser` | `PrescriptionParser` | LLM-based prescription text parser |
| `CHAT_MODEL_ID` | `str` | Active LLM model ID |
| `TIMING_LABEL_TO_SLOT` | `dict` | Maps UI labels → DB slot keys |
| `SLOT_TO_LABEL` | `dict` | Reverse mapping |
| `TIMING_SLOTS` | `list` | All 6 timing slot keys |

The internal `_search_agent` and `_router` are created here and injected into `chat_agent` but not exported directly.

---

### `backend/routers/chat.py` — Chat Endpoints

**Prefix:** `/api/chat`  **Tag:** `chat`

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/chat/history` | Returns all messages for the session as `{"messages": [...]}` |
| `DELETE` | `/api/chat/history` | Clears all messages and summaries; returns `{"cleared": true}` |
| `POST` | `/api/chat` | Text chat — SSE streaming response (see pipeline below) |
| `POST` | `/api/chat/audio` | Audio upload → transcription → SSE streaming response |

**Text pipeline (`POST /api/chat`):**
1. Validate that `message` is non-empty.
2. Run `emotion_agent.analyze_text()` in a thread-pool executor (blocking inference).
3. Emit `data: {"emotion": "...", "score": ...}`.
4. Delegate to `chat_agent.stream_async()` which handles routing, prompt building, and LLM streaming.
5. Forward all SSE chunks (`{"text": "token"}` … `{"done": true}`).

**Audio pipeline (`POST /api/chat/audio`):**
1. Read raw audio bytes from the multipart upload.
2. Transcribe via `audio_agent.transcribe_bytes()` (Groq Whisper).
3. Emit `data: {"transcribed": "..."}`.
4. Run `emotion_agent.analyze_audio()` on bytes + transcription.
5. Emit `data: {"emotion": "...", "score": ...}`.
6. Forward `chat_agent.stream_async()` chunks.

**SSE response headers:** `Cache-Control: no-cache`, `X-Accel-Buffering: no`.

---

### `backend/routers/medications.py` — Medication CRUD

**Prefix:** `/api/medications`  **Tag:** `medications`

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/medications` | List all medications with timing labels and available label options |
| `POST` | `/api/medications/manual` | Add a medication by name, dose notes, and timing labels |
| `DELETE` | `/api/medications/{row_id}` | Delete a medication by ID (404 if not found) |
| `POST` | `/api/medications/parse` | Parse a prescription text and preview extracted medications (no save) |
| `POST` | `/api/medications/save-parsed` | Parse a prescription text and save all extracted medications |

**Pydantic schemas:**
- `ManualMedRequest`: `name: str`, `dose_notes: str`, `timing_labels: list[str]`
- `ParseRequest`: `text: str`

**Timing label ↔ slot mapping** (via `TIMING_LABEL_TO_SLOT`):

| UI Label | DB Slot |
|---|---|
| Before Breakfast | `before_breakfast` |
| After Breakfast | `after_breakfast` |
| Before Lunch | `before_lunch` |
| After Lunch | `after_lunch` |
| Before Dinner | `before_dinner` |
| After Dinner | `after_dinner` |

---

### `backend/routers/dashboard.py` — Health Dashboard

**Prefix:** `/api/dashboard`  **Tag:** `dashboard`

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/dashboard/entries` | Raw `[TRACK]` log messages in the date range |
| `GET` | `/api/dashboard/chart-data` | Parsed metrics grouped by type for Recharts `LineChart` |
| `POST` | `/api/dashboard/trend` | Computes first→last change and % change for each metric |

**Trend computation pipeline:**
1. Receives `{"metrics": {"weight": {"first": 80, "last": 78, "unit": "kg"}, ...}}`.
2. Generates a self-contained Python script: `print(json.dumps({...}))`.
3. Runs the script in E2B via `CodeAgent.run()`.
4. Parses the JSON output. Falls back to local computation if the sandbox output is unparseable.
5. Returns `{"trends": {"weight": {"change": -2.0, "pct": -2.5, "direction": "down"}, ...}}`.

**`direction` field values:** `"up"` / `"down"` / `"flat"` based on sign of `change`.

---

### `backend/routers/emotion.py` — Standalone Emotion Endpoints

**Prefix:** `/api/emotion`  **Tag:** `emotion`

Standalone (non-streaming) JSON endpoints for emotion analysis. Useful for testing and external integrations.

| Method | Path | Input | Output |
|---|---|---|---|
| `POST` | `/api/emotion/text` | `{"text": "..."}` | `{emotion, score, all_scores, input_type}` |
| `POST` | `/api/emotion/audio` | Multipart audio file | `{emotion, score, transcription, all_scores, input_type}` |

**Audio path:** First transcribes via `audio_agent.transcribe_bytes()`, then calls `emotion_agent.analyze_audio(raw_bytes, filename, transcription=...)`.

---

## `routes/` — Query Routing & Enrichment

This layer intercepts every user message before it reaches the LLM and optionally enriches it with external context (web search results, local RAG, or sandbox output). The routing decision is made by the LLM itself, not by regex.

---

### `routes/base.py` — Shared Types

**`RouteResult` dataclass:**

| Field | Type | Description |
|---|---|---|
| `route_name` | `str` | `"drug"`, `"food"`, `"code"`, or `"general"` |
| `context` | `str \| None` | Context block injected into the LLM prompt; `None` = no enrichment |
| `metadata` | `dict` | Optional debug info (hit counts, source URLs, generated code) |

**`BaseRoute` abstract class:** Declares the `enrich(text) → RouteResult` interface that all route handlers must implement.

---

### `routes/router.py` — Query Classifier & Dispatcher

**Class:** `QueryRouter`

Uses the LLM to classify every user message into one of four categories, then dispatches to the correct route handler.

**Classification prompt (`_CLASSIFICATION_PROMPT`):** Describes the four categories in plain English with examples in English, Chinese, and Malay. The LLM must reply with exactly one word: `drug`, `food`, `code`, or `general`.

**`_classify(user_message)` method:**
- Calls the LLM with `temperature=0`, `max_tokens=5`.
- Validates the returned label against the allowed set.
- Falls back to `"general"` on any error or unexpected label.

**`route(user_message)` method:**

| Label | Dispatched to | Description |
|---|---|---|
| `drug` | `DrugRoute.enrich()` | Medication queries → web search |
| `food` | `FoodRoute.enrich()` | Food/diet queries → local RAG + web search |
| `code` | `CodeRoute.enrich()` | Calculation queries → LLM code gen + E2B sandbox |
| `general` | *(no enrichment)* | Everything else → `RouteResult(route_name="general", context=None)` |

---

### `routes/drug_route.py` — Medication Information

**Class:** `DrugRoute`

Enriches medication queries with live DuckDuckGo search results biased toward Singapore clinical sources.

**Pipeline:**
1. Call LLM (`_distill_query`) to convert the user's natural-language question into a 3–6 word search phrase (e.g., `"metformin diabetes side effects Singapore"`). Uses `temperature=0`, `max_tokens=20`.
2. Search via `SearchAgent.search(search_term)`.
3. Format up to 3 results as a markdown context block with `SYSTEM_PROMPT` prepended.

**System prompt:** Reminds the assistant to mention Singapore-specific brand names, CHAS/MediSave subsidies, and to advise consulting a doctor before changing medications.

**Returns:** `RouteResult(route_name="drug", context=..., metadata={"hits": N, "sources": [...]})`. If no results, `context=None`.

---

### `routes/food_route.py` — Food & Nutrition Information

**Class:** `FoodRoute`

Enriches food and diet queries using **two sources in parallel**:

1. **Local ChromaDB** (`FoodInfoRetriever.format_for_context()`): Queries the `sg_food_local` collection for Singapore hawker food and kopitiam drink data. Returns a markdown block with relevance scores.
2. **DuckDuckGo web search**: Uses an LLM-distilled search term (same approach as `DrugRoute`).

Both results are concatenated into a single context block with `SYSTEM_PROMPT`. If neither source returns data, `context=None`.

**System prompt:** Guides the assistant to provide Singapore-specific advice, cite specific nutritional values (calories, GI, sodium), suggest practical modifications (e.g., "kopi o kosong instead of teh tarik"), and tailor advice to the patient's condition.

---

### `routes/code_route.py` — Calculations via Python Sandbox

**Class:** `CodeRoute`

Handles mathematical and numerical calculation queries by:

1. **Generating Python code** (`_generate_code`): Calls the reasoning model (`$REASONING_MODEL_ID`, defaults to `Llama-SEA-LION-v3.5-70B-R`) with `thinking_mode: on` to produce a short, self-contained Python script.
2. **Extracting clean code** (`_extract_code`): Handles the reasoning model's tendency to prepend prose. Tries (in order): last fenced `\`\`\`python` block → trailing Python-looking lines → raw response as-is.
3. **Running the code** (`CodeAgent.run()`): Executes in E2B sandbox, captures stdout.
4. **Formatting context**: Returns a block containing the result and the code used.

**System prompt for final LLM reply:** Instructs the assistant to interpret the result conversationally and add relevant health context (e.g., daily calorie limits, medication dose context).

---

## `ingestion/` — Data Ingestion & Retrieval

### `ingestion/usermed_ingest.py` — Medication Schedule Database

Manages a personal medication schedule in SQLite. Also contains the LLM prescription parser.

**Constants:**

| Name | Value |
|---|---|
| `TIMING_SLOTS` | `["before_breakfast", "after_breakfast", "before_lunch", "after_lunch", "before_dinner", "after_dinner"]` |
| `TIMING_LABEL_TO_SLOT` | Mapping from UI display labels to DB column names |
| `SLOT_TO_LABEL` | Reverse of above |

---

#### `UserMedDB`

SQLite-backed store for the user's medication schedule.

**DB path:** `vectorstore/user_medications.db`

**Table `user_medications` schema:**

| Column | Type | Description |
|---|---|---|
| `id` | `INTEGER PK` | Auto-increment row ID |
| `medicine_name` | `TEXT` | Drug name |
| `before_breakfast` … `after_dinner` | `INTEGER (0/1)` | Six timing slot flags |
| `dose_notes` | `TEXT` | Free-text dose info (e.g., "1 tablet", "500 mg") |
| `created_at` | `TEXT` | ISO-8601 timestamp |

**Public methods:**

| Method | Description |
|---|---|
| `add_medication(medicine_name, timing_slots, dose_notes)` | Inserts a new row; returns the new `id`. |
| `delete_medication(row_id)` | Deletes by ID; returns `True` if a row was deleted. |
| `list_medications()` | Returns all medications as `list[dict]`. |
| `get_due_medications(slot)` | Returns all medications with the given timing slot flag set to 1. Used by reminder services. |
| `to_display_rows()` | Returns `[[id, name, dose_notes, schedule_string, created_at]]` for table display. |

---

#### `PrescriptionParser`

Uses the SEA-LION LLM to parse free-text prescription notes (in any language — English, Chinese, Malay, Tamil) into structured medication entries.

**`parse(prescription_text)` method:**
1. Sends the text to SEA-LION with a structured JSON extraction system prompt.
2. Strips any accidental markdown fences from the response.
3. Parses the JSON array.
4. Normalises and validates each entry (filters to known `TIMING_SLOTS`).
5. Returns `[{"medicine_name", "dose_notes", "timing": [slots]}]`.
6. Raises `ValueError` on LLM error or invalid JSON.

**Example multilingual handling:** `"三餐后"` (Chinese for "after every meal") → `["after_breakfast", "after_lunch", "after_dinner"]`.

**Module-level singletons** (imported by `backend/deps.py`):
- `user_med_db = UserMedDB()`
- `prescription_parser = PrescriptionParser()`

---

### `ingestion/foodinfo_ingest.py` — Food Knowledge Base

Ingests Singapore food data into ChromaDB and provides the retrieval interface for `FoodRoute`.

**Data sources:**
- `data/food/sg_hawker_food.json` — 20 hawker dishes with nutrition facts and disease-specific advice
- `data/food/sg_drinks_and_tips.json` — Kopitiam drink guide with calorie/sugar data and ordering tips

**ChromaDB collection:** `sg_food_local`  
**Embedding model:** `BAAI/bge-m3` (multilingual, high-quality)  
**Distance metric:** Cosine similarity

---

#### `HawkerChunker`

Produces **3 chunk types** per hawker food item to maximise retrieval recall for different query angles:

| Chunk ID | Content | Answers queries like… |
|---|---|---|
| `{food_id}_nutrition` | Calories, macros, GI, sodium, health tags | "What's in chicken rice?" |
| `{food_id}_advice_{disease}` | Risk level + English/Chinese guidance per disease | "Can I eat nasi lemak with diabetes?" |
| `{food_id}_alternatives` | Healthier swap suggestions with benefits | "What can I eat instead of char kway teow?" |

---

#### `DrinkChunker`

Produces chunks from the drinks JSON:

| Chunk ID | Content |
|---|---|
| `drink_{name}` | Per-drink: English/Chinese name, calories, sugar, notes |
| `drink_recs_diabetes` | Best/acceptable/limit/avoid drink lists for diabetes |
| `ordering_tips` | Local phrases (siu dai, kosong, less rice) in EN/CN/Malay |

---

#### `FoodInfoIngester`

Builds or refreshes the ChromaDB collection.

**`run()` method:** Calls `ingest_hawker()` then `ingest_drinks()`. Chunks are upserted in batches of 32 using BAAI/bge-m3 embeddings.

**Usage:**
```bash
python ingestion/foodinfo_ingest.py          # Build / refresh collection
python ingestion/foodinfo_ingest.py --test   # Smoke test retrieval with sample queries
```

---

#### `FoodInfoRetriever`

Query interface used by `FoodRoute`. Lazy-loads the embedding model on first call.

**`retrieve(query)` method:** Embeds the query and returns the top-`n_results` (default 4) matching chunks with `text`, `metadata`, and `distance` (0 = identical, 1 = orthogonal).

**`format_for_context(query)` method:** Calls `retrieve()` and formats results as a markdown block with relevance percentages (`round((1 − distance) × 100, 1)%`), ready for injection into the LLM prompt. Returns `None` if the collection is empty or no results match.

---

## `frontend/` — Next.js UI

Built with Next.js 14 (App Router), TypeScript, Tailwind CSS, and Recharts.

### `frontend/next.config.mjs` — Next.js Configuration

Rewrites all `/api/*` requests to `http://localhost:8000/api/*`, so the frontend and backend can run on different ports during development without CORS issues.

### `frontend/package.json` — Frontend Dependencies

| Dependency | Purpose |
|---|---|
| `next ^14.2.0` | App Router, SSR, file-based routing |
| `react ^18`, `react-dom ^18` | UI framework |
| `recharts ^2.12.0` | Health metric line charts on Dashboard |
| `lucide-react ^0.400.0` | Icon library |
| `tailwindcss ^3.4.0` | Utility-first CSS |
| `typescript ^5` | Type safety |

---

### `frontend/src/app/layout.tsx` — Root Layout

Sets the HTML `<title>` and `<meta description>`. Wraps every page with the `<Navbar>` component and a `<main>` flex container. Applies global CSS (`globals.css`).

---

### `frontend/src/components/Navbar.tsx` — Navigation Bar

Sticky top navigation bar with three links:

| Link | Route |
|---|---|
| 💬 Chat | `/chat` |
| 💊 Medications | `/medications` |
| 📊 Dashboard | `/dashboard` |

Uses `usePathname()` to highlight the active link with a filled pill style.

---

### `frontend/src/app/page.tsx` — Root Redirect

The root page (`/`) redirects users to `/chat` automatically.

---

### `frontend/src/app/chat/page.tsx` — Chat Page

The primary user interface. Features:

- **Message list** with user/assistant bubbles; user bubbles show an emotion badge (emoji + label + confidence %) sourced from the `emotion` SSE event.
- **Text input** (auto-resizing `<textarea>`) with `[TRACK]` quick-insert button.
- **Audio recording** via `MediaRecorder` API (webm format). Displays a live timer. On stop, uploads the blob to `POST /api/chat/audio` as multipart form data.
- **SSE consumer**: Parses the `data:` lines from the streaming response:
  - `{"transcribed": "..."}` → shows transcribed text in the input field
  - `{"emotion": "...", "score": ...}` → attaches to the current message bubble
  - `{"text": "token"}` → streams tokens into the assistant bubble
  - `{"done": true}` → finalises the response
- **History loading** on mount via `GET /api/chat/history`.
- **Clear history** menu option via `DELETE /api/chat/history`.

---

### `frontend/src/app/medications/page.tsx` — Medications Page

Medication schedule manager. Features:

- **Medication list** loaded from `GET /api/medications`, showing name, dose, schedule (timing labels), and date added.
- **Manual add form** with name, dose notes, and multi-select timing checkboxes → `POST /api/medications/manual`.
- **Prescription text parser**: Paste a doctor's note → `POST /api/medications/parse` for preview → `POST /api/medications/save-parsed` to save all.
- **Delete** button per row → `DELETE /api/medications/{id}`.

---

### `frontend/src/app/dashboard/page.tsx` — Dashboard Page

Health metrics dashboard. Features:

- **Date range picker** (start/end date inputs) that drives all data queries.
- **Recharts `LineChart`** per metric type, rendered from `GET /api/dashboard/chart-data`. Each chart shows data points labelled with value and unit.
- **Raw log table** from `GET /api/dashboard/entries` showing datetime and raw `[TRACK]` message text.
- **Trend panel** computed by `POST /api/dashboard/trend`. Shows a change badge (▲/▼/–) with absolute delta and percentage for each metric.

---

### `frontend/src/app/globals.css` — Global Styles

Imports Tailwind's base, components, and utilities layers. Defines the `brand` colour palette (used for primary buttons and active nav links) and base body typography.

---

## `data/` — Static Knowledge Base

Static JSON and PDF files shipped with the repository.

### `data/food/sg_hawker_food.json`

Array of 20 Singapore hawker dish objects. Each entry contains:
- `food_id`, `food_name_en`, `food_name_cn`, `food_name_malay`
- `category`, `cuisine`, `serving_size`
- `nutrition_per_serving`: `calories_kcal`, `carbohydrates_g`, `sugar_g`, `protein_g`, `total_fat_g`, `saturated_fat_g`, `sodium_mg`, `cholesterol_mg`, `fiber_g`
- `glycemic_index` (low/medium/high), `gi_value`
- `health_tags`: list of relevant tags
- `disease_advice`: per-disease (diabetes, hypertension, cardiovascular) objects with `risk_level`, `en` (English guidance), `cn` (Chinese guidance)
- `healthier_alternatives`: list of `{name_en, name_cn, benefit}`

**Ingested by:** `HawkerChunker` in `foodinfo_ingest.py` → `sg_food_local` ChromaDB collection.

---

### `data/food/sg_drinks_and_tips.json`

Kopitiam drink guide with:
- `kopitiam_drink_guide.terminology`: Per-drink entries (kopi, teh, milo, bandung, etc.) with English/Chinese names, calorie/sugar data, and notes.
- `kopitiam_drink_guide.diabetes_recommendations`: Lists of best/acceptable/limit/avoid drinks for diabetes patients.
- `local_food_ordering_tips.useful_phrases`: Ordering phrases (siu dai, kosong, less rice) in English, Chinese, and Malay.

**Ingested by:** `DrinkChunker` in `foodinfo_ingest.py` → `sg_food_local` ChromaDB collection.

---

### `data/drugs/diabetes_drugs.json`, `hypertension_drugs.json`, `lipid_drugs.json`

Structured drug reference data for common medications used in chronic disease management. These JSON files are **not yet ingested into ChromaDB** (drug queries currently rely on DuckDuckGo live search via `DrugRoute`). Listed as future work in `todos.md`.

---

### `data/emotion/emotion_support.json`

Emotion-specific response guidance for the LLM. Contains suggested response strategies and empathy cues for each detected emotion (happy, sad, angry, frustrated, fearful, neutral, confused).

---

### `data/clinical/ace_pdfs/`

Three PDF documents from the Singapore Academy of Medicine / Agency for Care Effectiveness (ACE):
- `ace_t2dm_2023.pdf` — Clinical practice guidelines for Type 2 Diabetes Mellitus
- `ace_t2dm_infographic.pdf` — T2DM infographic summary
- `ace_lipids_2023.pdf` — Clinical practice guidelines for lipid management

These PDFs are **not yet ingested** (a PDF route is listed as pending in `todos.md`). They are available for a future `pdf_route.py` that would chunk and embed these guidelines into ChromaDB.

---

## Runtime Stores (`vectorstore/`)

Created automatically at runtime under `vectorstore/`. Excluded from version control via `.gitignore`.

### `vectorstore/chat_memory.db` — SQLite (Chat & Health)

Shared by `MemoryManager` and `HealthTracker`.

| Table | Columns | Description |
|---|---|---|
| `chat_messages` | `id`, `session_id`, `role`, `content`, `created_at` | Full conversation history |
| `chat_summaries` | `session_id`, `summary`, `summarized_up_to`, `updated_at` | Rolling LLM-generated summary per session |
| `health_parsed_metrics` | `id`, `message_id`, `session_id`, `metric_type`, `value`, `unit`, `label`, `recorded_at` | Parsed `[TRACK]` metric values (LLM-extracted, cached) |

### `vectorstore/user_medications.db` — SQLite (Medications)

Managed by `UserMedDB`. Stores the personal medication schedule in the `user_medications` table.

### `vectorstore/chroma_db/` — ChromaDB (Food RAG)

Persistent ChromaDB vector store. Contains the `sg_food_local` collection with embeddings from `BAAI/bge-m3`. Populated by running `ingestion/foodinfo_ingest.py`. Queried by `FoodInfoRetriever` via cosine similarity search.

---

## Data Flow Diagrams

### Text Chat Request

```
Browser (POST /api/chat)
  │
  ▼
backend/routers/chat.py
  ├─ EmotionAgent.analyze_text()  ──► DistilRoBERTa
  │   └─ emit {"emotion": ..., "score": ...} SSE event
  │
  └─ ChatAgent.stream_async()
      ├─ MemoryManager.add_message("user", ...)
      ├─ [TRACK] check ──► skip LLM, emit "Tracked." SSE
      ├─ QueryRouter.route()
      │   ├─ LLM classifies: drug / food / code / general
      │   ├─ [drug]    DrugRoute  → LLM distill → DuckDuckGo → context
      │   ├─ [food]    FoodRoute  → ChromaDB + DuckDuckGo → context
      │   ├─ [code]    CodeRoute  → LLM code gen → E2B sandbox → context
      │   └─ [general] context = None
      ├─ build_api_messages(context, emotion_context)
      │   └─ system + rolling summary + short-term window
      ├─ AsyncOpenAI.chat.completions.create(stream=True)
      │   └─ emit {"text": "token"} SSE events per chunk
      ├─ MemoryManager.add_message("assistant", full_reply)
      └─ emit {"done": true}
```

### Health Dashboard Request

```
Browser (GET /api/dashboard/chart-data?start=&end=)
  │
  ▼
backend/routers/dashboard.py
  └─ HealthTracker.get_chart_data(start, end)
      ├─ Query SQLite: chat_messages WHERE content LIKE '[TRACK]%'
      ├─ For each message:
      │   ├─ Check health_parsed_metrics cache (message_id)
      │   └─ [cache miss] LLM extracts {metric_type, value, unit, label}
      │       └─ INSERT INTO health_parsed_metrics
      └─ Group by metric_type, sort by date
          └─ Return {"metrics": {"weight": {"label", "unit", "data": [...]}}}
```

### Audio Chat Request

```
Browser (POST /api/chat/audio, multipart)
  │
  ▼
backend/routers/chat.py
  ├─ AudioAgent.transcribe_bytes()  ──► Groq Whisper API
  │   └─ emit {"transcribed": "..."} SSE event
  ├─ EmotionAgent.analyze_audio(transcription=...)  ──► DistilRoBERTa
  │   └─ emit {"emotion": ..., "score": ...} SSE event
  └─ ChatAgent.stream_async(transcribed_text, ...)
      └─ (same pipeline as text chat above)
```