# CarePilot Event-Driven Multi-Agent Refactor Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the incremental, non-breaking refactor to explicit agent reasoning, deterministic orchestration, and complete event timeline coverage.

**Architecture:** Preserve existing feature workflows and services while formalizing agent adapters, deterministic merges, and timeline events. Orchestrators remain in `features/**` workflows; agents remain stateless; services execute side effects. All new agent invocations are shadow-first and gated by explicit feature logic.

**Tech Stack:** Python, FastAPI, pydantic, LangGraph, outbox/timeline, pytest.

---

## Scope Split Note
This plan spans multiple subsystems (chat, meals, meds, reminders, recommendations, timeline). If needed, split into separate plan docs per subsystem.

## File Structure Map (Targets)
- Modify: `src/care_pilot/features/**` (feature orchestrators)
- Modify: `src/care_pilot/agent/adapters/**` (BaseAgent wrappers)
- Modify: `src/care_pilot/features/**/workflows/**` (workflow orchestration)
- Modify: `src/care_pilot/platform/cache/timeline_service.py` (event timeline helpers)
- Modify: `docs/architecture/event-driven/event-coverage.md`
- Tests: `tests/agent/**`, `tests/api/**`, `tests/application/**`, `tests/features/**`, `tests/infrastructure/**`

---

## Chunk 1: Phase 3 — Feature-Orchestrated Agents

### Task 1: Inventory direct agent calls in features
**Files:**
- Modify: `docs/architecture/event-driven/event-coverage.md`

- [ ] **Step 1: Search for direct agent calls**

Run:
```bash
rg -n "agent\\.|run_.*_agent|infer_text|infer_speech|generate\\(" src/care_pilot/features
```
Expected: list of direct calls to agents or inference

- [ ] **Step 2: Record findings in event coverage doc**

Add a section:
```markdown
## Agent Invocation Audit
- [ ] <file>:<line> — <agent call>
```

- [ ] **Step 3: Commit**

```bash
git add docs/architecture/event-driven/event-coverage.md
git commit -m "docs: add agent invocation audit checklist"
```

### Task 2: Convert remaining feature orchestrators to BaseAgent adapters
**Files:**
- Modify: `src/care_pilot/features/companion/chat/orchestrator.py`
- Modify: `src/care_pilot/features/medications/medication_management.py`
- Modify: `src/care_pilot/features/meals/use_cases/confirm_meal.py`
- Modify: `src/care_pilot/features/recommendations/recommendation_service.py`
- Modify: `src/care_pilot/agent/adapters/shadow_agents.py`
- Test: `tests/api/test_api_recommendation_agent.py`
- Test: `tests/api/test_api_medications.py`
- Test: `tests/api/test_api_meal.py`

- [ ] **Step 1: Add missing adapters (if any)**

Example:
```python
class MedicationAgentAdapter(BaseAgent[MedicationAgentInput, MedicationAgentOutput]):
    name = "medication_agent_adapter"
    input_schema = MedicationAgentInput
    output_schema = MedicationAgentOutput

    def __init__(self, agent: MedicationAgent) -> None:
        self._agent = agent

    async def run(self, input_data: MedicationAgentInput, context: AgentContext) -> AgentResult[MedicationAgentOutput]:
        output = await self._agent.parse(input_data)
        return AgentResult(
            success=True,
            agent_name=self._agent.name,
            output=output,
            confidence=output.confidence,
            rationale="medication_parsed",
            warnings=[],
            errors=[],
            raw={"request_id": context.request_id, "correlation_id": context.correlation_id},
        )
```

- [ ] **Step 2: Replace direct agent calls with adapter.run(...)**

Example:
```python
adapter = MedicationAgentAdapter(deps.medication_agent)
result = await adapter.run(input_data, AgentContext(...))
output = result.output
```

- [ ] **Step 3: Ensure timeline emits `agent_action_proposed` using AgentResult**

Example:
```python
deps.event_timeline.append(
    event_type="agent_action_proposed",
    workflow_name="medication_intake",
    request_id=req_id,
    correlation_id=corr_id,
    user_id=user_id,
    payload={"agent_name": result.agent_name, "status": "success" if result.success else "error"},
)
```

- [ ] **Step 4: Run targeted tests**

Run:
```bash
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q \
  tests/api/test_api_recommendation_agent.py \
  tests/api/test_api_medications.py \
  tests/api/test_api_meal.py
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/care_pilot/features \
        src/care_pilot/agent/adapters/shadow_agents.py
git commit -m "refactor: use BaseAgent adapters in feature orchestrators"
```

---

## Chunk 2: Phase 4 — Event Timeline Expansion

### Task 3: Workflow event coverage audit
**Files:**
- Modify: `docs/architecture/event-driven/event-coverage.md`

- [ ] **Step 1: Audit workflow entry/exit events**

Run:
```bash
rg -n "workflow_started|workflow_completed|workflow_failed" src/care_pilot/features
```

- [ ] **Step 2: Fill missing entries in coverage doc**

Add missing event types per workflow.

- [ ] **Step 3: Commit**

```bash
git add docs/architecture/event-driven/event-coverage.md
git commit -m "docs: update workflow event coverage audit"
```

### Task 4: Add missing DomainEvents for key actions
**Files:**
- Modify: `src/care_pilot/features/**` (exact files from audit)
- Test: `tests/api/test_api_observability_contract.py`

- [ ] **Step 1: Add missing event emissions**

Example:
```python
event_timeline.append(
    event_type="medication_logged",
    workflow_name="medication_intake",
    request_id=req_id,
    correlation_id=corr_id,
    user_id=user_id,
    payload={"count": len(medications)},
)
```

- [ ] **Step 2: Update workflow trace emitter usage**

Ensure `workflow_started`/`workflow_completed` use `WorkflowTraceEmitter` when available.

- [ ] **Step 3: Run targeted tests**

Run:
```bash
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q tests/api/test_api_observability_contract.py
```
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/care_pilot/features
git commit -m "feat: expand workflow event timeline coverage"
```

---

## Chunk 3: Phase 5 — Decision Layer Hardening

### Task 5: Deterministic agent merge utilities
**Files:**
- Modify: `src/care_pilot/features/companion/chat/orchestrator.py`
- Test: `tests/agent/test_chat_stream_events.py`

- [ ] **Step 1: Add deterministic merge helper**

Example:
```python
def _merge_agent_actions(actions: list[dict]) -> list[dict]:
    seen: set[str] = set()
    merged: list[dict] = []
    for action in actions:
        key = f"{action.get('type')}::{action.get('message')}"
        if key in seen:
            continue
        seen.add(key)
        merged.append(action)
    return merged
```

- [ ] **Step 2: Apply merge in orchestrator without changing user-visible output**

Use the merged actions for telemetry only (no behavior change).

- [ ] **Step 3: Run tests**

Run:
```bash
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q tests/agent/test_chat_stream_events.py
```
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/care_pilot/features/companion/chat/orchestrator.py
git commit -m "refactor: deterministic merge utilities for agent actions"
```

### Task 6: Explicit safety/policy gating hooks
**Files:**
- Modify: `src/care_pilot/features/companion/chat/orchestrator.py`
- Test: `tests/domain/test_safety.py`

- [ ] **Step 1: Add explicit policy gate in orchestrator**

Example:
```python
policy = evaluate_text_safety(summary)
if policy.decision == "block":
    summary = "I can’t help with that request."
```

- [ ] **Step 2: Run tests**

Run:
```bash
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q tests/domain/test_safety.py
```
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/care_pilot/features/companion/chat/orchestrator.py
git commit -m "feat: explicit safety gating in chat orchestration"
```

---

## Chunk 4: Full Regression Sweep

### Task 7: Run full regression suite
**Files:**
- None (test only)

- [ ] **Step 1: Run backend lint/typecheck**

Run:
```bash
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run ruff check .
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run ty check . --extra-search-path src --output-format concise
```
Expected: PASS

- [ ] **Step 2: Run tests**

Run:
```bash
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q
```
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: full test sweep for event-driven refactor"
```
