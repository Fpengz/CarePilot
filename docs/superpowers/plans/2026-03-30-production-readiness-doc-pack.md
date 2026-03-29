# Production Readiness Doc Pack Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Document production topology, infra assumptions, and readiness dependencies without changing runtime behavior.

**Architecture:** This is a documentation-only hardening pass. We update the canonical runbook/config/roadmap and reflect completion in the production readiness checklist. No code changes or behavior changes.

**Tech Stack:** Markdown docs, existing validation scripts.

---

## Chunk 1: Operations Runbook — Production Topology

### Task 1: Add Production Topology + Readiness Dependencies
**Files:**
- Modify: `docs/references/operations-runbook.md`

- [ ] **Step 1: Add Production Topology section**

Insert after “Supported runtime profiles” and before “Readiness and health”:

```md
## Production Topology (Customer-Facing)

Required services:
- API runtime
- web runtime
- external worker
- SQLite (durable state)
- Redis (cache, coordination, worker signaling)

Optional services:
- inference runtime (separate service for heavy model execution)
- vector memory (if enabled by feature flags)

### Readiness Dependencies
- If Redis is enabled but unreachable, readiness should report `degraded`.
- Worker readiness depends on Redis when `EPHEMERAL_STATE_BACKEND=redis`.
- Inference runtime is optional; readiness should warn only when it is configured but unreachable.
```

- [ ] **Step 2: Run doc checks (no code changes)**

Run: `uv run python scripts/docs/validate_knowledge_base.py`
Expected: `Knowledge base validation passed.`

- [ ] **Step 3: Commit**

```bash
git add docs/references/operations-runbook.md
git commit -m "docs(runbook): document production topology"
```

---

## Chunk 2: Config Reference — Defaults + Required/Optional

### Task 2: Add Defaults & Dependency Table
**Files:**
- Modify: `docs/references/config-reference.md`

- [ ] **Step 1: Add “Infra Defaults & Dependencies” table**

Insert after “Environment loading conventions” and before “Auth / Session”:

```md
## Infra Defaults & Dependencies

| Setting | Default | Required? | Notes |
| --- | --- | --- | --- |
| `APP_ENV` | `dev` | yes | `staging`/`prod` tighten readiness checks. |
| `API_SQLITE_DB_PATH` | `care_pilot_api.db` | yes | Required for durable storage. |
| `AUTH_SQLITE_DB_PATH` | `care_pilot_auth.db` | yes | Required for auth persistence. |
| `EPHEMERAL_STATE_BACKEND` | `in_memory` | no | Use `redis` for production worker coordination. |
| `REDIS_URL` | none | conditional | Required when `EPHEMERAL_STATE_BACKEND=redis`. |
| `REDIS_NAMESPACE` | `care_pilot` | no | Namespaces worker keys and locks. |
| `READINESS_FAIL_ON_WARNINGS` | profile-derived | yes | `false` in dev, `true` in staging/prod. |
| `LLM_PROVIDER` | `test` | no | Set to real provider for production. |
```

- [ ] **Step 2: Run doc checks (no code changes)**

Run: `uv run python scripts/docs/validate_knowledge_base.py`
Expected: `Knowledge base validation passed.`

- [ ] **Step 3: Commit**

```bash
git add docs/references/config-reference.md
git commit -m "docs(config): add infra defaults table"
```

---

## Chunk 3: Roadmap + Checklist Alignment

### Task 3: Note topology clarification in roadmap
**Files:**
- Modify: `SYSTEM_ROADMAP.md`

- [ ] **Step 1: Add roadmap bullet**

Add under “Current Priorities”:

```md
- Deployment topology and infra assumptions clarified in docs.
```

- [ ] **Step 2: Commit**

```bash
git add SYSTEM_ROADMAP.md
git commit -m "docs(roadmap): note topology clarification"
```

### Task 4: Mark checklist items as doc-level complete
**Files:**
- Modify: `docs/exec-plans/active/2026-03-30-production-readiness-checklist.md`

- [ ] **Step 1: Mark doc-level completion**

Update these items to checked with “(doc-level complete)” appended:
- “Document required vs optional infra …”
- “Align runtime configuration defaults …”
- “Define production topology …”
- “Document required environment variables …”
- “Ensure infra control commands …”

Leave runtime-dependent items unchecked (e.g., worker scheduling under load).

- [ ] **Step 2: Run doc checks**

Run:
- `uv run python scripts/docs/validate_knowledge_base.py`
- `uv run python scripts/docs/doc_gardener.py`

Expected: “Knowledge base validation passed.” and no stale/deprecated items.

- [ ] **Step 3: Commit**

```bash
git add docs/exec-plans/active/2026-03-30-production-readiness-checklist.md
git commit -m "docs(exec-plans): mark doc-level readiness complete"
```

---

## Chunk 4: Final Integrity Pass

### Task 5: Final validation
**Files:**
- No file edits

- [ ] **Step 1: Run full doc validation**

Run:
- `uv run python scripts/docs/validate_knowledge_base.py`
- `uv run python scripts/docs/doc_gardener.py`

Expected: both pass cleanly.

---

## Notes on Review Loop
The plan requests subagent review per chunk. If subagents are unavailable, perform a manual self-review for placeholders, contradictions, and scope drift after each chunk.
