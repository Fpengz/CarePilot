# Agent Layer Audit + Refactor Spec (CarePilot)

**Date:** March 14, 2026  
**Owner:** Principal AI Systems Architect / Staff Backend Engineer  
**Constraint:** modular monolith, hackathon-ready + production credible  
**Scope:** clarify + harden `src/care_pilot/agent/**` and its boundaries

---

## 0) Executive summary (what changes, what doesn’t)

**What changes:** we treat the agent layer as the *only* home for model-powered reasoning/interpretation. Any direct model plumbing outside `care_pilot.agent` is a boundary violation and must be refactored behind the agent runtime.

**What doesn’t:** workflows stay in `features/**`, deterministic business logic stays in `features/**/domain` (and uses platform repos/ports), and infrastructure stays in `platform/**`.

---

## 1) Diagnosis of the current situation (failure modes + which apply here)

### Common failure modes in “messy agent layers”

- **Fake agents (services in disguise):** “Agent” modules doing CRUD, scheduling, formatting, or pure rules.
- **Agents doing deterministic logic:** business rules (eligibility, scheduling, safety gates) embedded in prompts/agent code.
- **Unclear workflows vs agents:** multi-step orchestration hidden in services/agents, instead of explicit use-cases/workflows.
- **LLM logic mixed with domain logic:** prompt + model selection + parsing living inside feature services or API modules.
- **Lack of typed contracts:** agents returning dicts/strings that drift over time.
- **Hidden orchestration in services:** “services” that effectively run workflows without workflow contracts/tracing.

### What applies in this repo (as of `ba8a5a1`, March 14, 2026)

The repo already has a strong intended architecture:

- **Agent layer:** `src/care_pilot/agent/**` (meal analysis, dietary reasoning, emotion, recommendations, chat)
- **Feature layer:** `src/care_pilot/features/**` (companion, meals, meds, reminders, etc.)
- **Platform layer:** `src/care_pilot/platform/**` (persistence, storage, auth, observability)

The biggest real risk is **LLM/model plumbing leaking outside the agent layer** (especially into “API-ish” feature modules). When that happens you lose:

- consistent schema validation + retry behavior
- consistent trace metadata (provider/model/capability/latency)
- a single choke point for cost controls and safety policy

**Concrete leak fixed in this refactor:** `src/care_pilot/features/meals/api_service.py` previously imported `pydantic_ai.Agent` and called `LLMFactory.get_model()` directly for label arbitration. That is now moved behind a typed agent-layer helper:

- `src/care_pilot/agent/meal_analysis/arbitration.py`

---

## 2) Design principles (governance rules)

1) **Agents own reasoning & interpretation** (unstructured → structured, judgment under uncertainty).
2) **Domain services own deterministic business logic** (rules, math, state transitions, persistence writes).
3) **Workflows coordinate product journeys** (sequencing, idempotency, partial failure handling).
4) **Tools/adapters isolate infrastructure** (LLM/OCR/search/storage/DB/notifications behind ports).
5) **Typed contracts are mandatory** (Pydantic inputs/outputs; bounded JSON).
6) **Minimize LLM calls** (heuristic-first routing; cache expensive inference; consolidate prompts).
7) **Deterministic policy is the final gate** (LLM may propose; policy decides).

**Standardization choices (refactor accelerators):**
- Use `pydantic_ai` for inference agents (through `src/care_pilot/agent/runtime/*` only).
- Use `pydantic-graph` for declared multi-step workflows.
- Reserve LangGraph for future workflows that require checkpointed persistence, interrupts, or long-lived thread state.

---

## 3) Target agent layer architecture (what is an agent; where code goes)

### What counts as an agent

An agent is a bounded capability that:
- takes **typed input** (Pydantic)
- performs **model-backed** inference or interpretation
- returns **typed output** (Pydantic) in an `AgentResult` envelope
- does **not** write durable state

### What does not count as an agent

- repositories and durable persistence
- schedulers and notification delivery
- deterministic calculators/rule engines
- API request parsing and HTTP error mapping
- workflow orchestration / multi-step journeys

### Interaction model

API → workflow/use-case (features) → (domain services + agents) → tools/adapters (platform)

The agent layer may call the inference runtime, and may call **read-only** domain services for context, but must not be the orchestrator.

---

## 4) Agent taxonomy (and what to actually use here)

### Categories

- **Perception agents:** unstructured inputs → structured facts (meal photo, prescription scan, emotion signals).
- **Reasoning agents:** structured context → assessments/proposals (dietary impact, adherence insights, recommendation synthesis).
- **Communication agents:** structured proposals → user/clinician text (companion reply, digest).
- **Planning agents:** propose next steps/questions (rare; only if product needs it).
- **Safety/policy agents:** generally avoid; keep policy deterministic; LLM critique is optional non-authoritative signal.

### Recommended taxonomy usage here

Use **perception + reasoning + communication** as first-class. Keep planning optional. Keep safety deterministic.

---

## 5) Proposed agent inventory (minimal, high-leverage)

| Agent | Category | Purpose | Inputs | Outputs | Must not own |
|---|---|---|---|---|---|
| `MealAnalysisAgent` | Perception | photo → meal perception | `MealAnalysisAgentInput` | `MealAnalysisAgentOutput` | persistence orchestration |
| `DietaryAgent` | Reasoning | meal + safety context → guidance | `DietaryAgentInput` | `AgentResponse` | policy enforcement, DB writes |
| `EmotionAgent` | Perception | text/audio → emotion signal | `EmotionTextAgentInput \| EmotionSpeechAgentInput` | `EmotionAgentOutput` | response generation |
| `RecommendationAgent` | Reasoning (often deterministic) | snapshot → recommendation bundle | `RecommendationAgentInput` | `RecommendationAgentOutput` | notifications, durable writes |
| `ChatAgent` + `QueryRouter` | Communication + routing | turn → response stream plan | `ChatInput` | `ChatOutput` | tool execution + persistence |

**Note:** where “recommendations” is deterministic, keep the service deterministic and treat the agent as a facade only when model reasoning is truly needed.

---

## 6) Layer boundaries (sharp rules)

### Agent layer (`src/care_pilot/agent/**`)
- May: inference calls via `InferenceEngine`; parse/validate to Pydantic outputs.
- Must: return `AgentResult` and include confidence + warnings/errors.
- Must not: durable writes; scheduling; multi-step orchestration; HTTP concepts.

### Workflow/application (`src/care_pilot/features/**`)
- May: orchestrate sequences; call agents + domain services; emit timeline events.
- Must: own idempotency + retries at the orchestration level.
- Must not: instantiate `pydantic_ai.Agent` or call `LLMFactory.get_model()` directly.

### Domain/services (`src/care_pilot/features/**/domain`)
- Must: deterministic; unit testable; persistence via platform ports.
- Must not: call LLMs or embed prompts.

### Platform/tools (`src/care_pilot/platform/**`)
- Must: infra-only; no product logic; no imports from `features` or `agent`.

---

## 7) Optimized request flows (reasoning vs deterministic)

### Meal photo upload
Workflow validates/stores media (deterministic) → `MealAnalysisAgent` (perception) → normalize + persist (deterministic) → `DietaryAgent` (reasoning) → policy gate (deterministic) → timeline event (deterministic).

### Prescription upload → reminders
Workflow stores doc (deterministic) → prescription extraction (perception agent) → regimen validation + scheduling (deterministic) → optional adherence insight (reasoning) → outbox/notifications (deterministic).

### Emotion-aware chat reply
Persist user message (deterministic) → emotion sidecar (perception) → snapshot assembly (deterministic) → optional recommendations (reasoning) → response generation (communication) → policy gate (deterministic) → persist assistant message (deterministic).

### Proactive recommendation
Deterministic triggers → recommendation synthesis (reasoning) → policy gate + rate limit (deterministic) → notifications (deterministic).

---

## 8) Contract design (bounded JSON + trace)

### Rules
- every model-backed call must request an **output schema**
- inference runtime handles **schema validation retries**
- agents return `AgentResult[OutputT]` with:
  - `confidence` (0–1)
  - `warnings/errors` (structured messages)
  - optional `raw` for debugging (bounded)

### Why this matters
It makes agents testable (golden inputs), debuggable (trace + schema), and safe to evolve (version schemas when needed).

---

## 9) Concrete repo refactor checklist (actionable)

### Immediate (hackathon cleanup)

- [x] Move ad-hoc model plumbing out of features:
  - ✅ `src/care_pilot/features/meals/api_service.py` → `src/care_pilot/agent/meal_analysis/arbitration.py`
- [x] Enforce boundary with a simple architecture test:
  - ✅ `tests/meta/test_agent_layer_boundaries.py`
- [ ] Inventory all agent packages; confirm each exposes 1 public entrypoint and typed contracts:
  - `src/care_pilot/agent/meal_analysis/agent.py`
  - `src/care_pilot/agent/dietary/agent.py`
  - `src/care_pilot/agent/emotion/agent.py`
  - `src/care_pilot/agent/recommendation/agent.py`
  - `src/care_pilot/agent/chat/agent.py`

### Next (post-demo hardening)

- Add import-boundary tests for platform purity (platform must not import features/agent).
- Add smoke tests for each agent contract (schema validation, empty/invalid inputs).
- Add cost controls: caching for vision + summarization; per-workflow LLM budgets.

### Later (extensibility)

- Offline evaluation harness + golden datasets (meal images, prescriptions, chat turns).
- Capability routing A/B (capability map + safe fallbacks).

---

## 10) Anti-patterns to avoid

- “Agent sprawl” (every feature becomes an agent).
- Business rules in prompts.
- Agents writing directly to DB.
- Orchestration hidden in services/routes.
- Unbounded free-form outputs in downstream code.
- LLM as final policy gate.
