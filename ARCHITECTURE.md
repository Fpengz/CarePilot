# Architecture

## Canonical Documentation

| Doc | Status | Last Verified | Owner |
| --- | --- | --- | --- |
| `ARCHITECTURE.md` | active | 2026-04-01 | platform |
| `README.md` | active | 2026-04-01 | platform |
| `SYSTEM_ROADMAP.md` | active | 2026-04-01 | platform |
| `AGENTS.md` | active | 2026-04-01 | platform |
| `docs/README.md` | active | 2026-04-01 | platform |
| `docs/ARCHITECTURE_AND_ROADMAP.md` | active | 2026-04-01 | platform |

## Purpose
This is the canonical architecture reference for CarePilot. It describes the feature-first modular-monolith structure, the ownership boundaries that contributors must preserve, and the forward direction for the project.

Primary direction: **event-driven workflows** are the mainline architecture. The orchestration-first design is **archived** and retained only as legacy exploration context.

Related docs:
- `README.md`
- `docs/exec-plans/index.md` — active/in-progress/completed execution plans
- `docs/references/REFACTOR_HISTORY.md` — log of completed architectural phases
- `docs/references/prompt_catalog.md` — repository of all agent prompts

---

## System Shape

CarePilot is a **feature-first modular monolith**: one codebase, strict layer ownership, no shared mutable globals. All work targets the canonical surfaces below.

```
src/care_pilot/
├── features/      product behavior and business entrypoints
├── agent/         bounded model-powered reasoning nodes
├── platform/      infrastructure and runtime adapters
├── core/          shared primitives and contracts
└── config/        settings composition root
```

### Repo-Wide Architecture Stance (Hard Decisions)
- **Features** own product behavior and deterministic domain rules.
- **Agent** owns model-backed reasoning (pydantic-ai).
- **LangGraph** is the canonical orchestration engine for all multi-step patient journeys.
- **Supervisor-led Orchestration**: A central Supervisor node interprets intent and routes to specialist nodes.
- **Archived**: Legacy synchronous orchestration and central "orchestrator-first" patterns are retired.
- **Safety First**: Every agent-proposed response MUST pass through a deterministic `safety_node` before reaching the user.
- **Platform** owns infra-only adapters.
- **Core** owns only tiny cross-cutting primitives and API contracts.

---

## Layers

### Interface Layer — `apps/web/`
- Next.js 14 app router; robust data fetching via **TanStack Query**.
- Optimized for low-latency via dynamic component loading and `content-visibility`.

### API Layer — `apps/api/carepilot_api/`
- Owns HTTP transport, session auth, and policy enforcement.
- **Thin Routers**: Handlers are transport-only. Deep orchestration logic is deferred to the Feature layer.

### Inference Layer — `apps/inference/run.py`
- Standalone microservice offloading heavy model execution (Whisper, BERT, Emotion) from the main API.
- Unified async runtime for speech and text emotion inference.
- Enables horizontal scaling of AI capabilities independent of the business logic.

### Persistence Layer — `src/care_pilot/platform/persistence/`
- **Schema Management**: Managed exclusively via **Alembic** migrations.
- **Relational Integrity**: Uses **SQLModel** for structured relational storage.
- **Default Runtime**: SQLite is the default durable store; Postgres is the scale path.
- **Normalization**: User profiles, nutrition goals, and meal schedules live in dedicated tables for integrity and query efficiency.

### Feature Layer — `src/care_pilot/features/`
- Owns all product behavior.
- **Workflows**: Coordinate multi-agent journeys using **LangGraph**.
- **Blackboard Model**: Uses `PatientCaseSnapshot` as a shared state object that agents read from and contribute to.

### Agent Layer — `src/care_pilot/agent/`
- Bounded reasoning nodes.
- **Supervisor Agent**: Top-level orchestrator node that interprets intent and routes to specialists.
- **Specialist Agents**: Perception (Meal, Meds) and Reasoning (Trend, Adherence, Care Plan) nodes.
- Agents return structured **`AgentResponse`** with proposed actions and recommendations.

---

## Event-Driven Workflows (Primary)

CarePilot uses an **event-driven** architecture with **LangGraph** only for explicit multi-step journeys.
The orchestration-first model is archived for feature exploration and should not be expanded.

```mermaid
graph TD
    START((Start)) --> Supervisor{Supervisor Agent}
    Supervisor -->|Intent: Meal| MealAgent[Meal Perception]
    Supervisor -->|Intent: Meds| MedAgent[Medication Parser]
    Supervisor -->|Intent: Trends| TrendAgent[Longitudinal Analyst]
    
    MealAgent --> Supervisor
    MedAgent --> Supervisor
    TrendAgent --> Supervisor
    
    Supervisor -->|Intent: Advice| CarePlanAgent[Care Strategy]
    CarePlanAgent --> Supervisor
    
    Supervisor -->|Done| END((End))
    
    subgraph "Shared Blackboard State"
        PatientCaseSnapshot
    end
```

### Strategic Rules:
1. **Agents Propose, Features Execute**: Agents return `AgentAction` objects; feature workflows validate and commit them.
2. **Deterministic Safety**: Safety filters run after agent reasoning but before user delivery.
3. **Traceability**: All agent reasoning steps are captured in `reasoning_trace` for observability.

---

## Validation Gates

All contributions must pass the following check suite:
- `uv run ruff check .` - Linting and formatting.
- `uv run ty check .` - Static type safety.
- `uv run pytest -q` - Functional correctness.
- `pnpm web:typecheck` - Frontend integrity.
