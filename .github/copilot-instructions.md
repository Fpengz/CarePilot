# Copilot Instructions

## Commands

**Backend validation (run in order):**
```bash
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run ruff check .
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run ty check . --extra-search-path src --output-format concise
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q
```

**Run a single test file:**
```bash
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest tests/domain/test_safety_engine.py -q
```

**Run a single test by name:**
```bash
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -k "test_compute_mcr_mixed_responses" -q
```

**Web validation:**
```bash
pnpm web:lint
pnpm web:typecheck
pnpm web:build
```

**Full-stack dev server:**
```bash
uv run python scripts/dg.py dev
```

**`SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0` is required** for all backend commands because the package uses `hatch-vcs` (version from git tags) and won't build without a tag or this override.

## Architecture

This is a **modular monolith** with strict layer ownership:

```
apps/api/dietary_api/   ← HTTP transport only: auth, policy, thin routers
src/dietary_guardian/
  application/          ← Use cases and orchestration (the "business logic" home)
  domain/               ← Typed contracts, deterministic rules, pure functions
  infrastructure/       ← Persistence, cache, LLM adapters, external integrations
  capabilities/         ← LLM/agent wrappers behind typed input/output contracts
  config/               ← Pydantic-settings composition (app.py + runtime.py)
apps/web/               ← Next.js frontend
apps/workers/           ← Async worker loop (reminder scheduler + outbox)
tests/                  ← Organized by architectural layer: domain/, application/, api/, etc.
```

**Request lifecycle:**
1. Router validates auth (`Depends(current_session)`) and policy (`require_action(session, "scope.action")`)
2. Router extracts a **scoped deps dataclass** (`meal_deps(get_context(request))`) and calls an application-layer function
3. Application function orchestrates domain logic + infrastructure adapters
4. Workers independently process reminders and outbox using distributed locks from `coordination_store`

**`AppContext`** (built once at startup in `deps.py`) holds all stores and agents. **Scoped deps dataclasses** (`MealDeps`, `WorkflowDeps`, `RecommendationDeps`, etc.) are slices of `AppContext` passed to application functions — this is how dependency injection works here, not FastAPI `Depends` chains.

**Safety is deterministic, not agent-driven.** `domain/safety/engine.py` runs threshold checks and drug interaction lookups before any LLM output is trusted. Agents propose; they never authorize or write durable state.

**`CaseSnapshot`** (defined in `domain/companion/`) is the canonical read model aggregating a patient's current state. New data sources should flow through the case snapshot before reaching personalization, engagement, or clinician digest logic.

## Key Conventions

### Layer rules (enforced by architecture)
- **Routers** import from `dietary_guardian.application.*` only — never from `services.*` or domain directly
- **Application layer** imports from `domain.*` and `infrastructure.*` — never from `apps.*`
- **Domain layer** must be pure: no infrastructure imports, no I/O. The one exception is `domain/safety/engine.py` which lazily imports `infrastructure.safety.drug_interaction_db` as a default only if no `DrugInteractionRepository` is injected
- **`application/meals/api_service.py`** is intentionally NOT exported from `application/meals/__init__.py` — this breaks a circular import with `capabilities/`

### Dependency injection pattern
```python
# Router (thin):
@router.post("/api/v1/meal/analyze")
async def meal_analyze(request: Request, session: dict = Depends(current_session)):
    require_action(session, "meal.analyze")
    return await analyze_meal(deps=meal_deps(get_context(request)), session=session, file=file)

# Application function (business logic):
async def analyze_meal(deps: MealDeps, session: dict, ...) -> MealAnalyzeResponse:
    ...
```

### Agent/capabilities pattern
All agents inherit `BaseAgent[InputT, OutputT]` from `capabilities/base.py` and return `AgentResult[OutputT]`. The envelope always has `success`, `output`, `confidence`, `warnings`, `errors`, `raw`. Agents are retrieved by name from `AgentRegistry` and never call stores or write state directly.

### Policy enforcement
All action names are defined in `apps/api/dietary_api/policy.py` as `POLICY_RULES`. Call `require_action(session, "scope.action")` at the top of every route handler. For resource-level checks (ownership), use `authorize_resource_action`.

### Settings
Config lives in `src/dietary_guardian/config/app.py` (composition root) and `runtime.py` (individual settings groups). Use `get_settings()` to access — it validates cross-field constraints (e.g., secrets required in prod, Redis required for external workers). Environment variables follow the pattern `SETTING_GROUP_FIELD_NAME` (e.g., `AUTH_STORE_BACKEND`, `LLM_PROVIDER`, `REDIS_URL`).

### Testing conventions
- **Domain tests**: Zero mocks — pure functions with deterministic inputs
- **Application tests**: Dataclass-based **fake stores** (not `unittest.mock`) injected as deps
- **Monkeypatch string paths** must match the actual import location after any renames — check for `monkeypatch.setattr("dietary_guardian.capabilities.X", ...)` when moving modules
- After major module moves, clear pycache: `find . -type d -name __pycache__ -exec rm -rf {} +`

### Backward-compat shims
Several shim `__init__.py` files exist at old paths (`domain/profiles/`, `domain/nutrition/`, `domain/care/`, `capabilities/schemas/`). These re-export from new locations with `# noqa: F401`. They are safe to delete once no external code references the old paths.

### Adding a new feature
Follow this sequence per `AGENTS.md`:
1. Define or extend domain contracts in `domain/<feature>/`
2. Add infrastructure adapter in `infrastructure/<feature>/`
3. Expose signal in `CaseSnapshot` if patient-facing
4. Implement use cases in `application/<feature>/use_cases.py`
5. Add thin router in `apps/api/dietary_api/routers/<feature>.py`
6. Register policy action in `policy.py`
7. Add scoped deps to `deps.py` if needed

### Commit format
`<type>(<scope>): <subject>` — Conventional Commits. Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.

### High-risk files — coordinate before touching
`config/app.py`, `infrastructure/persistence/*`, `infrastructure/auth/*`, `apps/api/dietary_api/deps.py`, `apps/api/dietary_api/policy.py`, `apps/workers/run.py`
