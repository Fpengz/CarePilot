# Workflows (Orchestration) Standard

This repo is a **modular monolith**. “Workflows” are the orchestration layer: they coordinate multi-step product journeys by calling **domain services** (deterministic) and **agents** (inference/reasoning), while keeping infrastructure behind platform adapters.

This document standardizes on:

- **Inference agents:** `pydantic_ai` (invoked via `src/dietary_guardian/agent/runtime/*` only)
- **Declared multi-step workflows:** `pydantic-graph`
- **Domain rules/persistence/scheduling:** deterministic in `src/dietary_guardian/features/**/domain`
- **LangGraph:** explicitly deferred (only for checkpointed persistence / interrupts / long-lived threads)

---

## Decision table (what to use when)

| Problem shape | Use | Why |
|---|---|---|
| Single-step orchestration (1–2 calls), minimal branching | Plain `use_cases.py` function | Lowest overhead, easy to test |
| Multi-step journey with explicit phases (validate → infer → persist → notify), branching, retries/idempotency, needs step-level trace | `pydantic-graph` | Declares steps + typed state + inspectable graph |
| Needs first-class checkpointed persistence, interrupts (“pause for user”), long-lived thread state, human-in-the-loop resumption | **LangGraph (future)** | Heavier runtime semantics; only adopt when required |

Rule of thumb: if you can’t easily answer “what are the steps and their inputs/outputs?” in a PR description, you should probably model it as a graph workflow.

---

## Boundary rules (hard constraints)

### Workflows may
- Call **agents** (reasoning/extraction) and **domain services** (deterministic rules + writes).
- Emit **timeline events** / trace events at each step.
- Own **idempotency**, retry policy (at workflow level), and compensation decisions.

### Workflows must not
- Instantiate `pydantic_ai.Agent` directly or call model factories directly.
  - Keep all model plumbing inside `src/dietary_guardian/agent/**` (guardrailed by tests).
- Own business rules, persistence writes, or scheduling algorithms.
  - Those live in `features/**/domain` and are unit-testable.
- Import `apps/api/**` or traffic in HTTP types (`Request`, `UploadFile`, etc.).

---

## Where workflows live (repo conventions)

- Keep workflow orchestration in the **feature layer**:
  - `src/dietary_guardian/features/<feature>/use_cases.py` (small flows)
  - `src/dietary_guardian/features/<feature>/workflows/*` (graph workflows)

Suggested layout for graph workflows:

```text
src/dietary_guardian/features/meals/workflows/
  meal_upload_graph.py
  types.py               # workflow state + output contracts
```

---

## `pydantic-graph` conventions (how we use it)

### 1) Typed workflow state

Workflow state is a Pydantic model that carries **only what the workflow needs between steps**:
- IDs / keys (user_id, session_id, request_id, idempotency_key)
- normalized inputs (safe, validated)
- intermediate typed outputs from agents/services (bounded)

Avoid putting repositories, DB connections, or large blobs into state.

### 2) Dependencies (`deps`)

Use a single dependencies object for runtime wiring (stores, settings, agent instances, tool registries). This keeps nodes pure and testable.

### 3) Nodes are small and single-purpose

Each node should:
- read/update state via `ctx.state`
- call exactly one “unit” (agent or domain service), or perform validation/branching
- return the next node or `End(output)`

### 4) Deterministic writes happen in domain services

If a node needs to persist, it calls a deterministic domain service method/function and stores only the resulting IDs/summaries back into state.

---

## Template: a graph workflow skeleton

This template uses the actual `pydantic-graph` API surface available in this repo environment:
- `Graph(nodes=[...])`
- `BaseNode.run(ctx: GraphRunContext) -> BaseNode | End[data]`
- `Graph.run(start_node, state=..., deps=..., persistence=...)`
- `graph.mermaid_code(...)` for diagrams

```python
from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel
from pydantic_graph import BaseNode, End, Graph, GraphRunContext, SimpleStatePersistence


class WorkflowState(BaseModel):
    user_id: str
    request_id: str
    idempotency_key: str
    # intermediate fields...


class WorkflowOutput(BaseModel):
    status: str
    # stable output contract...


@dataclass(frozen=True)
class WorkflowDeps:
    # settings: AppSettings
    # stores: AppStores
    # agents: AgentRegistry or specific agents
    pass


class ValidateInput(BaseNode[WorkflowState, WorkflowDeps, WorkflowOutput]):
    async def run(self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]) -> BaseNode | End[WorkflowOutput]:
        # validate ctx.state; set derived fields; decide branch
        return CallAgent()


class CallAgent(BaseNode[WorkflowState, WorkflowDeps, WorkflowOutput]):
    async def run(self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]) -> BaseNode | End[WorkflowOutput]:
        # agent_result = await deps.meal_agent.run(..., context=AgentContext(...))
        # ctx.state.some_field = agent_result.output.some_value
        return Persist()


class Persist(BaseNode[WorkflowState, WorkflowDeps, WorkflowOutput]):
    async def run(self, ctx: GraphRunContext[WorkflowState, WorkflowDeps]) -> BaseNode | End[WorkflowOutput]:
        # domain_service.persist(ctx.state...)  # deterministic write
        return End(WorkflowOutput(status="ok"))


workflow_graph = Graph(nodes=[ValidateInput, CallAgent, Persist], name="meal_upload")


async def run_workflow(*, deps: WorkflowDeps, state: WorkflowState) -> WorkflowOutput:
    persistence = SimpleStatePersistence()
    result = await workflow_graph.run(ValidateInput(), state=state, deps=deps, persistence=persistence)
    return result.output
```

### Diagram generation (recommended for PRs)

```python
diagram = workflow_graph.mermaid_code(title="Meal Upload Workflow")
```

Add the mermaid code to the PR description or a plan doc under `docs/plans/`.

---

## How this interacts with agents + policy

- Agents return structured proposals (`AgentResult[OutputT]`).
- Workflows decide whether to:
  - persist outputs,
  - ask follow-up questions,
  - or fall back to deterministic logic based on confidence thresholds.
- **Policy/safety remains deterministic** and gates what is emitted to users or sent via notifications.

---

## LangGraph (future) adoption criteria

Do not introduce LangGraph unless a workflow requires at least one of:
- checkpointed persistence of the workflow state across runs
- interrupts / “pause until user confirms”
- long-lived thread state and resumption semantics

When that happens, keep:
- **agents unchanged** (still `pydantic_ai` via agent runtime)
- **domain services unchanged** (deterministic)
- only swap the workflow runner implementation behind a small `WorkflowRunner` abstraction.

