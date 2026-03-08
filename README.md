# SEA-LION Health Assistant

A Singapore-focused health assistant for chronic-disease management (diabetes, hypertension, cardiovascular). Built with a **FastAPI** backend and **Next.js** frontend, powered by the [SEA-LION](https://sea-lion.ai/) LLM and Groq Whisper for audio transcription.

---

## Features

- 💬 **Streaming chat** — SSE-based token-by-token responses
- 🎤 **Audio input** — record voice directly in the browser (Groq Whisper transcription)
- � **Emotion detection** — DistilRoBERTa classifies user emotion from text (or transcription for audio) and injects it as empathy context into the LLM system prompt
- 📍 **Health tracking** — prefix any message with `[TRACK]` to log a metric (e.g. `[TRACK] weight 80kg`)
- 📊 **Dashboard** — line charts of tracked health metrics; trend computation runs in an [E2B](https://e2b.dev/) cloud sandbox
- 💊 **Medications** — manage personal medication schedules
- 🧠 **Memory** — rolling summary + short-term window across sessions (SQLite)
- 🔍 **RAG routing** — queries are routed to drug, food, or general knowledge retrievers
- 🐍 **Python sandbox** — calculation queries are translated to Python by the LLM and executed securely in an E2B sandbox

---

## Folder Structure

```
agent/
├── .env                        # API keys (see setup below)
│
├── agents/                     # Core agent logic — no framework dependencies
│   ├── chat_agent.py           # LLM streaming, prompt building, memory, routing
│   ├── audio_agent.py          # Groq Whisper transcription (bytes or numpy)
│   ├── emotion_agent.py        # DistilRoBERTa emotion classifier (singleton, lazy-loading)
│   ├── code_agent.py           # E2B sandbox wrapper — runs generated Python securely
│   ├── health_tracker.py       # [TRACK] parsing, LLM metric extraction, chart data
│   ├── memory_manager.py       # SQLite-backed short-term + rolling summary memory
│   └── search_agent.py         # Web search retriever
│
├── backend/                    # FastAPI application
│   ├── main.py                 # App entry point, CORS, router registration
│   ├── deps.py                 # Singleton agent/client instances
│   └── routers/
│       ├── chat.py             # GET/POST /api/chat, POST /api/chat/audio, DELETE /api/chat/history
│       ├── dashboard.py        # GET /api/dashboard/chart-data, /entries; POST /trend (E2B sandbox)
│       ├── emotion.py          # POST /api/emotion/text, /api/emotion/audio (standalone JSON)
│       └── medications.py      # CRUD for personal medication schedule
│
├── frontend/                   # Next.js 14 application (TypeScript + Tailwind)
│   └── src/app/
│       ├── chat/page.tsx       # Chat UI — streaming, audio recording, [TRACK] button
│       ├── dashboard/page.tsx  # Health metrics dashboard (Recharts line charts)
│       └── medications/page.tsx# Medication management
│
├── routes/                     # LLM-based query router (drug / food / general)
│
├── ingestion/                  # Data ingestion scripts for ChromaDB + SQLite
│
├── data/                       # Static knowledge base
│   ├── drugs/                  # Drug JSON files (diabetes, hypertension, lipids)
│   ├── food/                   # Singapore hawker food + drinks data
│   └── clinical/               # ACE clinical guideline PDFs
│
├── vectorstore/                # Auto-created at runtime
│   ├── chat_memory.db          # SQLite: chat history, summaries, health metrics
│   └── chroma/                 # ChromaDB vector collections
│
└── main.py                     # Legacy Gradio app (not used by the web stack)
```

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- API keys for SEA-LION and Groq (see below)

---

## Setup

### 1. Clone & create `.env`

Create a `.env` file in the project root:

```env
SEALION_API=<your SEA-LION API key>
CHAT_MODEL_ID=aisingapore/Gemma-SEA-LION-v4-27B-IT
GROQ_API_KEY=<your Groq API key>
TRANSCRIPTION_MODEL_ID=MERaLiON/MERaLiON-2-3B
E2B_API_KEY=<your E2B API key>
REASONING_MODEL_ID=aisingapore/Llama-SEA-LION-v3.5-70B-R
```

| Key                  | Where to get it                                                |
| -------------------- | -------------------------------------------------------------- |
| `SEALION_API`        | [sea-lion.ai](https://sea-lion.ai/)                            |
| `GROQ_API_KEY`       | [console.groq.com](https://console.groq.com/)                  |
| `E2B_API_KEY`        | [e2b.dev](https://e2b.dev/)                                    |
| `REASONING_MODEL_ID` | Optional — defaults to `aisingapore/Llama-SEA-LION-v3.5-70B-R` |

---

### 2. Backend (FastAPI)

```bash
# From the project root
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Start the server:

```bash
# From the project root
.venv/bin/uvicorn backend.main:app --reload --port 8000
```

Verify it's running:

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

---

### 3. Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

The app will be available at **http://localhost:3000** (auto-redirects to `/chat`).

> The Next.js config proxies all `/api/*` requests to `http://localhost:8000`, so both servers must be running.

---

## Running the App

Open two terminals:

**Terminal 1 — Backend**

```bash
cd /path/to/agent
.venv/bin/uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend**

```bash
cd /path/to/agent/frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## API Endpoints

| Method   | Path                           | Description                                                           |
| -------- | ------------------------------ | --------------------------------------------------------------------- |
| `GET`    | `/api/chat/history`            | Load conversation history                                             |
| `POST`   | `/api/chat`                    | Send a message (SSE streaming, emotion-aware)                         |
| `DELETE` | `/api/chat/history`            | Clear conversation history                                            |
| `POST`   | `/api/chat/audio`              | Upload audio → Groq Whisper → emotion → SSE reply                     |
| `GET`    | `/api/medications`             | List all medications                                                  |
| `POST`   | `/api/medications/manual`      | Add a medication manually                                             |
| `DELETE` | `/api/medications/{id}`        | Delete a medication                                                   |
| `POST`   | `/api/medications/parse`       | Preview-parse a prescription                                          |
| `POST`   | `/api/medications/save-parsed` | Save parsed medications                                               |
| `GET`    | `/api/dashboard/chart-data`    | Parsed metric data for charts (`?start=&end=`)                        |
| `GET`    | `/api/dashboard/entries`       | Raw `[TRACK]` log entries (`?start=&end=`)                            |
| `POST`   | `/api/dashboard/trend`         | First→last change per metric, computed in E2B Python sandbox          |
| `POST`   | `/api/emotion/text`            | `{ "text": "..." }` → `{ emotion, score, all_scores }`                |
| `POST`   | `/api/emotion/audio`           | Audio file → Groq transcription → `{ emotion, score, transcription }` |

---

## Health Tracking

Prefix any chat message with `[TRACK]` to log a health metric:

```
[TRACK] weight 80 kg
[TRACK] blood pressure 140/90 mmHg
[TRACK] fasting blood glucose 7.2 mmol/L
[TRACK] felt fatigued, severity 6/10
```

The message is saved instantly ("Tracked." reply — no LLM call). View your metrics on the **Dashboard** tab with a date range selector. The **Trend** panel on the dashboard calls `POST /api/dashboard/trend`, which generates and runs a Python script inside an [E2B](https://e2b.dev/) cloud sandbox to compute first→last change and percentage change for each metric safely.

---

## Emotion Detection

Every chat message (text or transcribed audio) is run through [`j-hartmann/emotion-english-distilroberta-base`](https://huggingface.co/j-hartmann/emotion-english-distilroberta-base) (downloaded automatically from HuggingFace on first use, ~330 MB).

| Input | Pipeline                                                     |
| ----- | ------------------------------------------------------------ |
| Text  | DistilRoBERTa on the raw message                             |
| Audio | Groq Whisper transcription → DistilRoBERTa on the transcript |

The detected emotion and confidence score are:

- Emitted as an SSE event `{"emotion": "sad", "score": 0.87}` before the first text token
- Shown as a badge on the user's message bubble in the chat UI
- Injected into the LLM system prompt so the assistant responds with appropriate empathy

Supported labels: `happy`, `sad`, `angry`, `frustrated`, `fearful`, `neutral`, `confused`.

---

## Python Sandbox (E2B)

Calculation and computation queries are handled by the **code route**:

1. The LLM generates a short, self-contained Python script for the user's question.
2. The script is executed in an [E2B](https://e2b.dev/) cloud sandbox (`CodeAgent`).
3. The sandbox output is fed back to the LLM as context for a conversational final reply.

The dashboard **Trend** endpoint uses the same `CodeAgent` to compute metric deltas server-side.

Requires `E2B_API_KEY` in `.env`.

---

## Databases

The app uses three persistent stores, all created automatically at runtime under `vectorstore/`.

### `vectorstore/chat_memory.db` — SQLite

Shared by `MemoryManager` and `HealthTracker`. Contains three tables:

| Table                   | Purpose                                                                                  |
| ----------------------- | ---------------------------------------------------------------------------------------- |
| `chat_messages`         | Full message history (`session_id`, `role`, `content`, `created_at`)                     |
| `chat_summaries`        | Rolling LLM-generated summary per session — older messages compressed into one text blob |
| `health_parsed_metrics` | Parsed `[TRACK]` metric values (`metric_type`, `value`, `unit`, `recorded_at`)           |

The short-term prompt window keeps the last 3 messages in memory; everything older is compressed into the rolling summary by the LLM automatically.

---

### `vectorstore/user_medications.db` — SQLite

Managed by `UserMedStore` in `ingestion/usermed_ingest.py`. Stores the user's personal medication schedule — name, dose, frequency, duration, and notes. Used by the Medications tab and the `/api/medications/*` endpoints.

---

### `vectorstore/chroma_db/` — ChromaDB (persistent)

A local vector database with a single collection:

| Collection      | Contents                                                                | Distance |
| --------------- | ----------------------------------------------------------------------- | -------- |
| `sg_food_local` | Singapore hawker food items and kopitiam drinks from `data/food/` JSONs | cosine   |

Populated by running `ingestion/foodinfo_ingest.py`. Queried by the food route (`routes/food_route.py`) for RAG-based food and nutrition lookups.
