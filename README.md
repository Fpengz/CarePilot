# 🍲 Dietary Guardian SG
**Singapore Innovation Challenge 2026: Clinical-Grade Dietary Monitoring**

"Culture-First, Safety-Always." Optimized for Singapore's aging population (The "Mr. Tan" Persona).

---

## 🚀 Quick Start (Astral Stack)

Ensure you have [uv](https://github.com/astral-sh/uv) installed.

### 1. Environment Setup
```bash
# Clone and sync dependencies
uv sync

# Configure environment variables
export GOOGLE_API_KEY="your-api-key"
# Optional: Disable remote logfire for local dev
export LOGFIRE_TOKEN="" 
# Optional: local runtime auth (used by Ollama/vLLM profile mode)
export LOCAL_LLM_API_KEY="ollama"
```

### 2. Run the Application
```bash
# Start the Streamlit Interface
PYTHONPATH=src uv run streamlit run src/app.py
```

### 2a. Local Model Testing (Ollama / vLLM)
```bash
# Ollama example
ollama serve
ollama pull llama3

# vLLM example (separate shell)
uv run python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-7B-Instruct \
  --host 0.0.0.0 --port 8000
```

Then in the app sidebar:
- Set `Model runtime` to `local`
- Choose profile `ollama_qwen3-vl:4b` or `vllm_qwen`
- Optionally override model name / base URL for local experiments

### 2b. Telegram Dev Notifications
```bash
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"
export TELEGRAM_DEV_MODE="1"  # dev mode skips real network sends
```

In the app sidebar, include channels under `Notification channels`:
- `in_app` and `push` are always available.
- `telegram` sends to Telegram Bot API (or skips network in dev mode).
- `whatsapp` and `wechat` are modular stubs in this version (`whatsapp://stub`, `wechat://stub`) for adapter integration.

### 2c. Debug Logging
```bash
export DIETARY_GUARDIAN_LOG_LEVEL="INFO"
```

Model request logs include destination trace fields:
- `provider`
- `model`
- `endpoint`
- `request_id`
- `user_id` (when available)

Notification logs include:
- `channel`
- `destination`
- `event_id`
- `attempt`
- `success`/`failure`

### 3. CLI Demonstration
```bash
# Run the core logic scenarios (High Sodium & Safety Violation)
PYTHONPATH=src uv run python src/main.py
```

---

## 🧪 Testing & Quality Gates

Our system uses a multi-tiered verification strategy to ensure 0% critical safety violations.

### 1. Static Analysis (The Astral Standard)
```bash
# Linting and Formatting
uv run ruff check .

# Strict Type Checking
uv run ty check . --extra-search-path src --output-format concise
```

### 2. Unit & Integration Tests
```bash
# Run the full test suite
uv run pytest -q
```

### 3. Clinical Simulation (Hypothesis)
We use property-based testing to simulate "Virtual Patients" and stress-test the safety engine against 10,000+ randomized meal scenarios.
```bash
# Run property-based safety tests
uv run pytest -q tests/test_virtual_patient.py
```

---

## 🏗️ Architecture Summary

- **Perception (`Hawker Vision`):** Gemini-3-Flash with Tier 3 Fallback to Health Promotion Board (HPB) standards.
- **Reasoning (`Dietary Agent`):** Pydantic-AI with localized "Uncle Guardian" persona and structured Pydantic outputs.
- **Safety (`Safety Engine`):** Deterministic interceptor backed by `DrugInteractionDB` (SQLite/Mock) and nutritional threshold monitoring.
- **Social (`Social Service`):** Block-level gamification for "Kampong Spirit" healthy eating challenges.
- **Observability (`Logfire`):** Real-time instrumentation for clinical-grade tracing and validation.

---

## 📊 Current Project Status (v0.1.0)

| Feature | Implementation | Notes |
| :--- | :--- | :--- |
| **Safety Logic** | 100% | Deterministic clinical interceptor active. |
| **Vision AI** | 90% | Gemini-3-Flash integrated + HPB Fallback logic. |
| **Singlish Persona** | 100% | "Uncle Guardian" agent fully tuned. |
| **Social Dashboard** | 60% | Block scores and leaderboard implemented in Streamlit. |
| **Persistence** | 40% | SQLite schema in place; session state used for prototypes. |

---

## 🔒 Image Handling Policy
- Meal photos from upload/camera are processed in-memory for analysis.
- Raw image bytes are not persisted to database or long-term storage.
- Only derived metadata and analysis outputs are kept in session state.

---

## 🇸🇬 Localization: "Hawker Vision 2.0"
Identifies nuances like:
- **Mee Rebus:** Thick gravy + yellow noodles.
- **Mee Siam:** Thin vermicelli + tangy/thin gravy.
- **Laksa:** Coconut milk base + "hum" detection.

---
**Senior AI Architect (Google)**
*Singapore Innovation Challenge 2026 Commit*
