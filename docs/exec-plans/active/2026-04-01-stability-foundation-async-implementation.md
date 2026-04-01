# Stability Foundation: Config Centralization and Async I/O Refactor Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Centralize configuration using `pydantic-settings` and refactor the system to use fully async I/O for database and HTTP operations.

**Architecture:** 
1.  Migrate `src/care_pilot/config/` to use `BaseSettings` for all configuration.
2.  Switch from synchronous `Session` and `Engine` to `AsyncSession` and `create_async_engine` in SQLModel.
3.  Update repository interfaces and services to use `async/await` and `httpx.AsyncClient`.
4.  Refactor FastAPI dependencies to provide async sessions.

**Tech Stack:** Python, SQLModel (SQLAlchemy 2.0 Async), Pydantic Settings, HTTPX, FastAPI.

---

## Chunk 1: Config Centralization

### Task 1: Migrate to `pydantic-settings`

**Files:**
- Modify: `pyproject.toml` (Add `pydantic-settings`)
- Create: `src/care_pilot/config/base.py` (Base settings classes)
- Modify: `src/care_pilot/config/settings.py` (Final unified settings)

- [ ] **Step 1: Add `pydantic-settings` to dependencies**

Run: `uv add pydantic-settings`

- [ ] **Step 2: Define structured settings in `src/care_pilot/config/base.py`**
  Organize into subgroups: `APISettings`, `DatabaseSettings`, `LogfireSettings`, etc.

- [ ] **Step 3: Update `src/care_pilot/config/settings.py` to inherit from `BaseSettings`**

- [ ] **Step 4: Verify config loading**

- [ ] **Step 5: Commit**

---

## Chunk 2: Async Database Foundation

### Task 2: Refactor SQLModel for Async Support

**Files:**
- Modify: `src/care_pilot/platform/persistence/sqlite_repository.py`
- Modify: `apps/api/carepilot_api/deps.py`

- [ ] **Step 1: Update engine creation to use `sqlite+aiosqlite`**

- [ ] **Step 2: Implement `get_async_session` dependency**

- [ ] **Step 3: Refactor repository methods to be `async`**

- [ ] **Step 4: Run persistence tests**

- [ ] **Step 5: Commit**

---

## Chunk 3: Async HTTP & Service Layer

### Task 3: Refactor Services and HTTP Clients

**Files:**
- Modify: `src/care_pilot/platform/adapters/http_client.py` (Switch to AsyncClient)
- Modify: `src/care_pilot/features/profiles/profile_service.py` (Example service refactor)

- [ ] **Step 1: Replace `httpx.Client` with `httpx.AsyncClient`**

- [ ] **Step 2: Update service signatures to use `async def`**

- [ ] **Step 3: Verify with unit tests**

- [ ] **Step 4: Commit**

---

## Chunk 4: Final Verification

### Task 4: System-wide validation

- [ ] **Step 1: Run comprehensive gate**

Run: `uv run python scripts/cli.py test comprehensive`

- [ ] **Step 2: Verify Logfire traces show async spans**

- [ ] **Step 3: Commit and Open PR**
