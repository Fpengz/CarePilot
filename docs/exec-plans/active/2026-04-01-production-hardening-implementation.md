# Production Hardening: Health Checks and Worker Scheduling Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement comprehensive health checks for API, Workers, and Inference runtime, and ensure predictable worker scheduling.

**Architecture:** 
1.  Add a `/health` endpoint to the FastAPI app that checks DB connectivity and basic service readiness.
2.  Implement a standard `HealthCheck` protocol for background workers.
3.  Add health check logic to the inference runtime (Emotion/Recommendation agents).
4.  Refine worker scheduling intervals and concurrency settings in `AppSettings`.

**Tech Stack:** Python, FastAPI, SQLModel, Logfire.

---

## Chunk 1: API Health Checks

### Task 1: Implement `/health` endpoint

**Files:**
- Modify: `apps/api/carepilot_api/routers/health.py`
- Modify: `src/care_pilot/platform/persistence/engine.py` (Add DB ping)

- [ ] **Step 1: Implement `ping_db` in `engine.py`**
  ```python
  def ping_db() -> bool:
      try:
          with get_db_engine().connect() as conn:
              conn.execute(text("SELECT 1"))
          return True
      except Exception:
          return False
  ```

- [ ] **Step 2: Update `/health` router to include DB status**

- [ ] **Step 3: Run API tests to verify health endpoint**

- [ ] **Step 4: Commit**

---

## Chunk 2: Worker & Inference Health

### Task 2: Implement Worker Health Monitoring

**Files:**
- Modify: `apps/workers/run.py`
- Modify: `src/care_pilot/platform/app_context.py` (Aggregate health)

- [ ] **Step 1: Add health state tracking to background workers**
  Store last-run timestamp and status in a shared (ephemeral) state or memory.

- [ ] **Step 2: Add health check method to `EmotionAgent`**

- [ ] **Step 3: Expose aggregated health in `AppContext`**

- [ ] **Step 4: Commit**

---

## Chunk 3: Scheduling Hardening

### Task 3: Refine Worker Scheduling

**Files:**
- Modify: `src/care_pilot/config/runtime.py`

- [ ] **Step 1: Review and adjust default intervals for `WorkerSettings`**

- [ ] **Step 2: Document scheduling logic in `docs/references/operations-runbook.md`**

- [ ] **Step 3: Commit**

---

## Chunk 4: Final Verification

### Task 4: Production Readiness Gate

- [ ] **Step 1: Verify `/health` returns 200 with all components UP**

- [ ] **Step 2: Run comprehensive gate**

Run: `uv run python scripts/cli.py test comprehensive`

- [ ] **Step 3: Commit and Open PR**
