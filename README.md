# SEA-LION Health Assistant

A Singapore-focused health assistant for chronic-disease management (diabetes, hypertension, cardiovascular). Built with a **FastAPI** backend and **Next.js** frontend, powered by the [SEA-LION](https://sea-lion.ai/) LLM and Groq Whisper for audio transcription.

---

## Features

- 💬 **Streaming chat** — SSE-based token-by-token responses
- 🎤 **Audio input** — record voice directly in the browser (Groq Whisper transcription)
- 📍 **Health tracking** — prefix any message with `[TRACK]` to log a metric (e.g. `[TRACK] weight 80kg`)
- 📊 **Dashboard** — line charts of tracked health metrics over a date range
- 💊 **Medications** — manage personal medication schedules
- 🧠 **Memory** — rolling summary + short-term window across sessions (SQLite)
- 🔍 **RAG routing** — queries are routed to drug, food, or general knowledge retrievers

---

## Folder Structure

```
agent/
├── .env                        # API keys (see setup below)
│
├── agents/                     # Core agent logic — no framework dependencies
│   ├── chat_agent.py           # LLM streaming, prompt building, memory, routing
│   ├── audio_agent.py          # Groq Whisper transcription (bytes or numpy)
│   ├── health_tracker.py       # [TRACK] parsing, LLM metric extraction, chart data
│   ├── memory_manager.py       # SQLite-backed short-term + rolling summary memory
│   └── search_agent.py         # Web search retriever
│
├── backend/                    # FastAPI application
│   ├── main.py                 # App entry point, CORS, router registration
│   ├── deps.py                 # Singleton agent/client instances
│   └── routers/
│       ├── chat.py             # GET/POST /api/chat, POST /api/chat/audio, DELETE /api/chat/history
│       ├── dashboard.py        # GET /api/dashboard/chart-data, /api/dashboard/entries
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
```

| Key            | Where to get it                               |
| -------------- | --------------------------------------------- |
| `SEALION_API`  | [sea-lion.ai](https://sea-lion.ai/)           |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com/) |

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

| Method   | Path                           | Description                                    |
| -------- | ------------------------------ | ---------------------------------------------- |
| `GET`    | `/api/chat/history`            | Load conversation history                      |
| `POST`   | `/api/chat`                    | Send a message (SSE streaming)                 |
| `DELETE` | `/api/chat/history`            | Clear conversation history                     |
| `POST`   | `/api/chat/audio`              | Upload audio → transcribe → SSE reply          |
| `GET`    | `/api/medications`             | List all medications                           |
| `POST`   | `/api/medications/manual`      | Add a medication manually                      |
| `DELETE` | `/api/medications/{id}`        | Delete a medication                            |
| `POST`   | `/api/medications/parse`       | Preview-parse a prescription                   |
| `POST`   | `/api/medications/save-parsed` | Save parsed medications                        |
| `GET`    | `/api/dashboard/chart-data`    | Parsed metric data for charts (`?start=&end=`) |
| `GET`    | `/api/dashboard/entries`       | Raw `[TRACK]` log entries (`?start=&end=`)     |

---

## Health Tracking

Prefix any chat message with `[TRACK]` to log a health metric:

```
[TRACK] weight 80 kg
[TRACK] blood pressure 140/90 mmHg
[TRACK] fasting blood glucose 7.2 mmol/L
[TRACK] felt fatigued, severity 6/10
```

The message is saved instantly ("Tracked." reply — no LLM call). View your metrics on the **Dashboard** tab with a date range selector.
