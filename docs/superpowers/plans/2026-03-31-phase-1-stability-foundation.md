# Phase 1 Stability Foundation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a rock-solid, observable, and performant core foundation for CarePilot by centralizing configuration, refactoring to asynchronous I/O, and unifying observability with Logfire.

**Architecture:** We will implement a "Platform-First" refactor. Observability and Configuration will be unified at the platform layer, and persistence will be migrated to asynchronous sessions.

**Tech Stack:** Logfire, Pydantic-Settings, SQLModel (Async), FastAPI (Async).

---

## Chunk 1: Observability Setup (Logfire)

### Task 1.1: Unified Logfire Initialization

**Files:**
- Create: `src/care_pilot/platform/observability/setup.py`
- Modify: `src/care_pilot/platform/observability/__init__.py`

- [ ] **Step 1: Write initialization logic**

```python
import logfire
from care_pilot.config.app import get_settings

def setup_observability():
    settings = get_settings()
    logfire.configure(
        token=settings.observability.logfire_token,
        environment=settings.app.environment,
        service_name="care-pilot-api"
    )
    # Instrument FastAPI, SQLModel, HTTPX here in later steps
```

- [ ] **Step 2: Commit**

```bash
git add src/care_pilot/platform/observability/setup.py
git commit -m "feat(observability): add unified logfire initialization"
```

### Task 1.2: Instrument FastAPI and SQLModel

**Files:**
- Modify: `apps/api/run.py`
- Modify: `src/care_pilot/platform/persistence/engine.py`

- [ ] **Step 1: Add FastAPI Middleware**

```python
from logfire.integrations.fastapi import LogfireMiddleware
app.add_middleware(LogfireMiddleware)
```

- [ ] **Step 2: Instrument SQLModel Engine**

```python
import logfire
logfire.instrument_sqlalchemy(engine)
```

- [ ] **Step 3: Commit**

```bash
git add apps/api/run.py src/care_pilot/platform/persistence/engine.py
git commit -m "feat(observability): instrument FastAPI and SQLModel with logfire"
```

---

## Chunk 2: Log Consolidation (Replace print)

### Task 2.1: Mass-replace print() with logfire.info()

**Files:**
- Modify: All files in `src/care_pilot/` with `print(`

- [ ] **Step 1: Identify and replace prints**

- [ ] **Step 2: Commit**

```bash
git commit -m "refactor(observability): replace print() with logfire.info()"
```

---

## Chunk 3: Config Centralization (Pydantic Settings)

### Task 3.1: Migrate to BaseSettings

**Files:**
- Modify: `src/care_pilot/config/app.py`
- Modify: `src/care_pilot/config/runtime.py`

- [ ] **Step 1: Inherit from BaseSettings**

```python
from pydantic_settings import BaseSettings

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    # ... fields
```

- [ ] **Step 2: Commit**

```bash
git commit -m "feat(config): migrate to pydantic-settings for .env management"
```

---

## Chunk 4: Async I/O Refactor (Database)

### Task 4.1: Async DB Sessions

**Files:**
- Modify: `src/care_pilot/platform/persistence/engine.py`
- Modify: `src/care_pilot/platform/persistence/db_session.py`

- [ ] **Step 1: Switch to AsyncEngine and AsyncSession**

- [ ] **Step 2: Commit**

```bash
git commit -m "feat(persistence): refactor to AsyncEngine and AsyncSession"
```
