# GEMINI.md - Project Manifesto & System Architecture

## 1. Project Vision: "The Singapore Innovation Challenge 2026"
**Goal:** Create the world's most robust, localized, and clinical-grade "Dietary Guardian" for Singapore's aging population.
**Core Philosophy:** "Culture-First, Safety-Always." We do not ban local food; we optimize it.

### The Persona: "Mr. Tan"
- **Profile:** 68 years old, retired taxi driver.
- **Conditions:** Type 2 Diabetes (HbA1c ~7.5%), Hypertension, Hyperlipidemia.
- **Lifestyle:** Eats at hawker centers 5-7 times a week.
- **Pain Point:** "Doctor says no oily food, but I don't know what to eat at the coffee shop."

---

## 2. Strategic Differentiation ("The Winning Edge")

### A. "Hawker Vision 2.0" (Hyper-Localized Intelligence)
Generic AI fails on "Char Kway Teow" vs. "Fried Kway Teow". Our system understands:
- **Nuance:** Identifies "hum" (cockles), lard cubes, and gravy viscosity.
- **Volumetric Estimation:** Uses reference objects (spoon/coin) or LiDAR (on supported devices) to estimate *actual* portion size, not just "small/medium/large".
- **Actionable Advice:** Instead of "Don't eat this," we say: *"Ask for less hum and no lard; eat only half the noodles to save 200kcal for dinner."*

### B. The "Metabolic Digital Twin" (Predictive Health)
We don't just log food; we predict its impact.
- **Simulation:** Uses a physiological model to predict post-prandial glucose spikes based on meal composition and Mr. Tan's specific metabolic history.
- **Feedback:** "If you eat this whole bowl, your sugar will likely spike to 14.0 mmol/L. Eat half and walk 10 mins to keep it under 10.0."

### C. The "Kampong Spirit" (Community & Social)
Health is a team sport in Singapore.
- **Block-Level Challenges:** Anonymized, aggregate health scores for residential blocks (e.g., "Block 105 vs. Block 106: Who cut more sugar this week?").
- **Family Bridge:** Weekly WhatsApp summaries for "Mr. Tan's" daughter, flagging anomalies like "Dad skipped lunch" or "High sodium intake for 3 days."

### D. "Uncle-Friendly" Interaction (Singlish NLP)
- **Voice-First:** Recognizes "Uncle" / "Auntie" vernacular.
- **Code-Switching:** Handles mixed English/Malay/Hokkien queries like "Can eat or not? Verify got pork?"

---

## 3. Technical Stack: The "2026 Google Standard"
We leverage the **Astral Unified Toolchain** for a deterministic, high-performance Python environment.

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Package Manager** | `uv` (Astral) | Instant, deterministic dependency resolution. |
| **Type System** | `ty` (Astral) | Static analysis for medical-grade code safety. |
| **Linting** | `ruff` (Astral) | Enforces strict PEP compliance and style. |
| **AI Orchestration** | `Pydantic-AI` | Structured, type-safe agentic workflows. |
| **LLM (Perception)** | `gemini-3-flash` | Sub-second image recognition (Food/Medicine). |
| **LLM (Reasoning)** | `gemini-3.1-pro` | Complex clinical synthesis and empathy. |
| **Data Validation** | `Pydantic` | Runtime schema enforcement for all I/O. |
| **Config Mgmt** | `Hydra` + `hydra-zen` | Compositional configuration with validation. |
| **Doc Parsing** | `MarkItDown` | High-fidelity extraction from medical PDFs. |
| **Database** | `SQLite` + `Litestream` | Local-first, robust, serverless replication. |
| **Testing** | `Hypothesis` | Property-based testing for safety rules. |

---

## 4. System Architecture: The "Dietary Guardian"

### Layer 1: The Perception Engine (Input)
- **Multi-Modal Ingest:**
  - **Photos:** Meal images, Medicine labels.
  - **Documents:** HealthHub PDF reports (Lab results).
  - **Voice:** "I just ate a bowl of Laksa."
- **Processing:** `gemini-3-flash` converts raw input into structured `MealEvent` or `BiomarkerUpdate` objects.

### Layer 2: The Reasoning Core (Processing)
- **Context Window:** Maintains a rolling 7-day "Metabolic State" of the user.
- **Agent:** `DietaryAgent` analyzes the `MealEvent` against the `Metabolic State`.
- **Logic:** "Sodium budget remaining: 400mg. Detected Meal: 1200mg. Alert Level: High."

### Layer 3: The Safety Valve (Verification)
- **The "Do No Harm" Check:** 
  - Queries `DrugInteractionDB` (Local SQLite/Graph).
  - *Rule:* If `User.meds.contains("MAOI")` AND `Meal.contains("Tyramine_Rich")` -> **BLOCK RESPONSE**.
- **Fail-Safe:** If the Safety Layer triggers, the AI response is replaced with a hard-coded medical safety warning.

### Layer 4: The Interaction Layer (Output)
- **Persona-Aligned Voice:** Singlish-friendly but respectful (e.g., using "Uncle" or "Sir" appropriately).
- **Channel:** Mobile App UI / WhatsApp Bot.

---

## 5. Engineering Standards & Quality Gates

### Configuration and Runtime Contract
- Single source of truth for environment configuration is `Settings` in `src/dietary_guardian/config/settings.py`.
- Runtime modules must load configuration through `get_settings()`; feature modules must not read environment variables directly with `os.getenv`.
- Provider-specific requirements are mandatory at runtime:
  - `llm_provider=gemini` requires `GEMINI_API_KEY` or `GOOGLE_API_KEY`.
  - `llm_provider=ollama` or `llm_provider=vllm` requires a local base URL (`LOCAL_LLM_BASE_URL` or `OLLAMA_BASE_URL`).
- Configuration validation is fail-fast and must be treated as a startup contract, not a recoverable warning path.

### A. The "Virtual Patient" Test Suite (Clinical Simulation)
We do not test on production users first.
- **Simulation:** A CI pipeline runs "Virtual Mr. Tan" through 10,000 randomized meal scenarios using `Hypothesis`.
- **Pass Criteria:** 0% Critical Safety Violations (e.g., recommending sugar to a diabetic in hypoglycemia).

### B. Strict Typing & Validation
- No `Dict[str, Any]`. All data flows must be defined as `Pydantic` models.
- `ty check . --strict` must pass before any commit.

### C. Evaluation Metrics
1.  **Safety Violation Rate:** Must be 0%.
2.  **Food Recognition Accuracy:** Verified against SG FoodID dataset.
3.  **User Adherence:** % of "Actionable Advice" accepted by the user.
4.  **System Latency:** < 2s for voice response (critical for conversational flow).

### Development Workflow Standards
- Pre-commit hooks are mandatory and must run on every commit.
- Conventional Commits are required: `<type>(<scope>): <subject>`.
- Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- Repository commit template is `.gitmessage` (set with `git config commit.template .gitmessage`).
- Required hook checks:
  - `uv run ruff check .`
  - `uv run ty check . --extra-search-path src --output-format concise`
- Required verification gates before merge:
  - `uv run ruff check .`
  - `uv run ty check . --extra-search-path src --output-format concise`
  - `uv run pytest -q`

---

## 6. Roadmap & Implementation Status

| Phase | Description | Status | Key Features |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **The Core** | **Complete** | `uv` setup, `Pydantic` models, `DietaryAgent` (Pydantic-AI) with Singlish persona. |
| **Phase 2** | **The Eyes** | **V1 Complete** | `HawkerVisionModule` with `gemini-3-flash` and HPB-backed safety fallback logic. |
| **Phase 3** | **The Brain** | **V1 Complete** | `SafetyEngine` with deterministic clinical checks and `DrugInteractionDB`. |
| **Phase 4** | **The Heart** | **In Progress** | `SocialService` for block-level challenges and "Kampong Spirit" gamification. |
| **Phase 5** | **The Interface** | **In Progress** | Streamlit-based "Uncle Guardian" dashboard with multi-tab clinical view. |

---

## 7. Current System Capabilities (v0.1.0)

1.  **Deterministic Safety Intercepts:** Before any AI reasoning, the `SafetyEngine` checks for clinical contraindications (e.g., Warfarin vs. Vitamin K / Spinach).
2.  **Multimodal Vision Pipeline:** `HawkerVision` identifies SG-specific dishes and applies "Safe-Fail" logic—if AI confidence is low, it swaps to HPB standard values.
3.  **Singlish Personality:** The agent uses an empathetic "Uncle" persona, switching to a firm clinical tone for safety violations.
4.  **Local-First Persistence:** Clinical data and block-level scores are managed via local SQLite/Dictionary stores for sub-second performance.
5.  **Virtual Patient Testing:** A dedicated `Hypothesis` suite simulates thousands of "Mr. Tan" scenarios to ensure safety rules never break.
