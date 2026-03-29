# Workflows (Orchestration) Standard

This repo is a **modular monolith**. “Workflows” are the orchestration layer: they coordinate multi-step product journeys by calling **domain services** (deterministic) and **agents** (inference/reasoning), while keeping infrastructure behind platform adapters.

This document standardizes on:

- **Inference agents:** `pydantic_ai` (invoked via `src/care_pilot/agent/runtime/*` only)
- **Declared multi-step workflows:** **LangGraph**
- **Domain rules/persistence/scheduling:** deterministic in `src/care_pilot/features/**/domain`

---

## Decision table (what to use when)

| Problem shape | Use | Why |
|---|---|---|
| Single-step orchestration (1–2 calls), minimal branching | Plain `use_cases.py` function | Lowest overhead, easy to test |
| Multi-step journey with explicit phases (validate → infer → persist → notify), branching, retries/idempotency, needs step-level trace | **LangGraph** | Declares steps + typed state + inspectable graph |
| Needs first-class checkpointed persistence, interrupts (“pause for user”), long-lived thread state, human-in-the-loop resumption | **LangGraph** | LangGraph already provides checkpointing/interrupt semantics when needed |

Rule of thumb: if you can’t easily answer “what are the steps and their inputs/outputs?” in a PR description, you should probably model it as a graph workflow.

---

## Boundary rules (hard constraints)

### Workflows may
- Call **agents** (reasoning/extraction) and **domain services** (deterministic rules + writes).
- Emit **timeline events** / trace events at each step.
- Own **idempotency**, retry policy (at workflow level), and compensation decisions.

### Workflows must not
- Instantiate `pydantic_ai.Agent` directly or call model factories directly.
  - Keep all model plumbing inside `src/care_pilot/agent/**` (guardrailed by tests).
- Own business rules, persistence writes, or scheduling algorithms.
  - Those live in `features/**/domain` and are unit-testable.
- Import `apps/api/**` or traffic in HTTP types (`Request`, `UploadFile`, etc.).

---

## Message Channels (Inbound/Outbound)

Message channels are now the canonical interface for reminders and chat‑style interactions:

- **Outbound:** workflows enqueue `OutboundMessage` records (via the alert outbox) with optional attachments.
- **Inbound:** channel webhooks normalize into message payloads, create or reuse a **message thread**, then run chat orchestration.
- **Threads:** one persistent thread per `(user + channel + endpoint)`; all inbound/outbound messages are stored in `message_thread_messages`.

Inbound workflows must:
- create or reuse the thread
- persist inbound message
- run chat orchestration
- persist outbound response
- enqueue outbound delivery

---

## Where workflows live (repo conventions)

- Keep workflow orchestration in the **feature layer**:
  - `src/care_pilot/features/<feature>/use_cases.py` (small flows)
  - `src/care_pilot/features/<feature>/workflows/*` (graph workflows)

Suggested layout for graph workflows:

```text
src/care_pilot/features/meals/workflows/
  meal_upload_graph.py
  types.py               # workflow state + output contracts
```

---

## LangGraph conventions (how we use it)

### 1) Typed workflow state

Workflow state is a typed container that carries **only what the workflow needs between steps**:
- IDs / keys (user_id, session_id, request_id, idempotency_key)
- normalized inputs (safe, validated)
- intermediate typed outputs from agents/services (bounded)

Avoid putting repositories, DB connections, or large blobs into state.

### 2) Dependencies (`deps`)

Use a single dependencies object for runtime wiring (stores, settings, agent instances, tool registries). This keeps nodes pure and testable. Pass `deps` into the graph builder and close over it in node implementations.

### 3) Nodes are small and single-purpose

Each node should:
- read/update state via the `state` object
- call exactly one “unit” (agent or domain service), or perform validation/branching
- return a dict of state updates

### 4) Deterministic writes happen in domain services

If a node needs to persist, it calls a deterministic domain service method/function and stores only the resulting IDs/summaries back into state.

---

## Template: a LangGraph workflow skeleton

This template matches the LangGraph API surface used in this repo:
- `StateGraph(StateType)`
- `workflow.add_node`, `workflow.add_edge`
- `workflow.compile()` + `graph.ainvoke(...)`

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class WorkflowState(TypedDict):
    user_id: str
    request_id: str
    idempotency_key: str
    # intermediate fields...


class WorkflowOutput(TypedDict):
    status: str
    # stable output contract...


@dataclass(frozen=True)
class WorkflowDeps:
    # settings: AppSettings
    # stores: AppStores
    # agents: AgentRegistry or specific agents
    pass


def build_workflow_graph(*, deps: WorkflowDeps) -> StateGraph:
    async def validate_node(state: WorkflowState) -> dict[str, object]:
        # validate state; set derived fields; decide branch
        return {}

    async def call_agent_node(state: WorkflowState) -> dict[str, object]:
        # agent_result = await deps.meal_agent.run(..., context=AgentContext(...))
        # return {"some_field": agent_result.output.some_value}
        return {}

    async def persist_node(state: WorkflowState) -> dict[str, object]:
        # domain_service.persist(state...)  # deterministic write
        return {"output": {"status": "ok"}}

    workflow = StateGraph(WorkflowState)
    workflow.add_node("validate", validate_node)
    workflow.add_node("call_agent", call_agent_node)
    workflow.add_node("persist", persist_node)

    workflow.add_edge(START, "validate")
    workflow.add_edge("validate", "call_agent")
    workflow.add_edge("call_agent", "persist")
    workflow.add_edge("persist", END)
    return workflow


async def run_workflow(*, deps: WorkflowDeps, state: WorkflowState) -> WorkflowOutput:
    graph = build_workflow_graph(deps=deps).compile()
    final_state = await graph.ainvoke(state)
    return final_state["output"]
```

### Diagram generation (recommended for PRs)

```python
# LangGraph can emit Mermaid once you call .get_graph()
mermaid = build_workflow_graph(deps=deps).get_graph().draw_mermaid()
```

Add the mermaid code to the PR description or a plan doc under `docs/exec-plans/active/`.

---

## How this interacts with agents + policy

- Agents return structured proposals (`AgentResult[OutputT]`).
- Workflows decide whether to:
  - persist outputs,
  - ask follow-up questions,
  - or fall back to deterministic logic based on confidence thresholds.
- **Policy/safety remains deterministic** and gates what is emitted to users or sent via notifications.

---

## Agent Context Builder (Policy + Selection)

To control token bloat and improve auditability, context assembly has two layers:

1. **Policy layer** — what data the agent is allowed to see.
2. **Selection layer** — what data is relevant right now.

Both layers should be logged for auditability:

- Policy log: “Was this data allowed?”
- Selection log: “Why was this data selected?”
