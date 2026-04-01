# Agent Workflow Contract

## Canonical Documentation

| Doc | Status | Last Verified | Owner |
| --- | --- | --- | --- |
| `AGENTS.md` | active | 2026-04-01 | platform |
| `README.md` | active | 2026-04-01 | platform |
| `ARCHITECTURE.md` | active | 2026-04-01 | platform |
| `SYSTEM_ROADMAP.md` | active | 2026-04-01 | platform |
| `docs/README.md` | active | 2026-04-01 | platform |
| `docs/ARCHITECTURE_AND_ROADMAP.md` | active | 2026-04-01 | platform |

## Purpose
This file defines how human contributors and AI agents should collaborate on the companion architecture in this repository.

It supplements:
- `README.md`
- `ARCHITECTURE.md`
- `SYSTEM_ROADMAP.md`
- `docs/README.md`

## Repository Knowledge Map
Treat this file as a table of contents. The system of record lives in `docs/`.

Start here:
- `docs/README.md` — knowledge base index
- `docs/design-docs/index.md` — architecture + design references
- `docs/exec-plans/index.md` — active, in-progress, completed plans + templates
- `docs/product-specs/index.md` — product behavior and user specs
- `docs/references/index.md` — API, ops, config, and engineering references
- `docs/QUALITY_SCORE.md`, `docs/RELIABILITY.md`, `docs/SECURITY.md`

## Product Direction
The current branch is optimizing for a hackathon-quality AI health companion, not backward compatibility.

Every change should strengthen at least one of:
- proactive patient engagement
- multi-source personalization
- clinician-facing insight quality
- measurable health impact
- architectural extensibility

## Roles
- `Planner`: defines decision-complete scope, contracts, validation, rollout, and risks.
- `Implementer`: executes the approved scope with the minimum coherent change set.
- `Reviewer`: checks correctness, regressions, safety, and boundary hygiene.

## Required Task Contract
Every multi-agent task must define:
- `Goal`
- `Scope`
- `Files`
- `Validation`
- `Risk`

## Harness Engineering Rules
All agentic workflows must follow the Anthropic Harness Design Principles:
- **Generator-Evaluator Separation**: Never let the same agent instance grade its own work. Use a separate `Reviewer` role or a verification tool (e.g., Playwright, Pytest) to validate outputs.
- **Sprint Contracts**: Every task must begin with a negotiated contract (Definition of Done) in `docs/exec-plans/`.
- **Context Compaction**: When a conversation or plan exceeds 10 turns, summarize the current state into a "Handoff Artifact" and reset the context.
- **Evidence-Based Critique**: Evaluators must provide specific, tool-derived evidence (logs, test failures, screenshots) rather than general feedback.

## Naming and Documentation Standards
Strict adherence to these naming patterns is required:
- **Execution Plans**: `docs/exec-plans/{active|in-progress|completed}/YYYY-MM-DD-<slug>.md`
- **Design Docs**: `docs/design-docs/<domain>/<slug>.md` (e.g., `docs/design-docs/architecture/meal-analysis.md`)
- **Product Specs**: `docs/product-specs/<slug>.md`
- **Feature Services**: `src/care_pilot/features/<feature>/<name>_service.py`
- **Agent Modules**: `src/care_pilot/agent/<name>/agent.py`
- **Tests**: `tests/<layer>/test_<name>.py` (Backend) or `<name>.test.tsx` (Frontend)

## Mandatory Validation Gate
- **Pre-commit Tests**: All backend and frontend unit tests must be green before a commit is allowed. This is enforced via pre-commit hooks.
- **No Manual Overrides**: Do not use `--no-verify` to bypass failing tests on features or bugfixes.

## Housekeeping Automation
The system runs overnight housekeeping to maintain repository health:
- **Unfinished Plans**: `in-progress` plans older than 7 days with no updates are automatically **promoted** to today's date to ensure they remain in the active cycle.
- **Temporary Artifacts**: Files in `data/runtime/` older than 3 days are purged.
- **Index Integrity**: Housekeeping verifies that all docs are correctly indexed in `docs/README.md`.

## Architecture Ownership Map
- Transport/API: `apps/api/carepilot_api/**`
- Web UX: `apps/web/**`
- Worker/runtime: `apps/workers/**`
- Core primitives: `src/care_pilot/core/**`
- Feature behavior: `src/care_pilot/features/**`
- Agent capabilities: `src/care_pilot/agent/**`
- Platform adapters: `src/care_pilot/platform/**`
- Documentation: `README.md`, `ARCHITECTURE.md`, `SYSTEM_ROADMAP.md`, `docs/**`

## Canonical Companion Modules
Changes that affect patient guidance, clinician summaries, or impact tracking should prefer these modules:
- `features/companion/core`
- `features/companion/personalization`
- `features/companion/engagement`
- `features/companion/care_plans`
- `features/companion/clinician_digest`
- `features/companion/impact`
- `features/companion/interactions`

Do not put new business logic primarily in route handlers.

## Agent Design Rules
- Default to deterministic logic before adding an agent.
- Add a new agent only when specialization materially improves reasoning quality.
- Agents must use typed input/output contracts.
- Agents must not write durable state directly.
- Safety and policy checks remain outside prompts.
- **Inference standard:** model-powered agents use `pydantic_ai` via `src/care_pilot/agent/runtime/*` (no direct `pydantic_ai.Agent` usage outside `src/care_pilot/agent/**`).
- **Workflow standard:** declared multi-step product journeys use **LangGraph** (typed workflow state + explicit steps). Keep domain rules/persistence/scheduling deterministic in `features/**/domain`.
- **LangGraph policy:** LangGraph is the default workflow engine. Use its checkpoint/interrupt capabilities only when a workflow truly requires them, but keep deterministic domain rules in `features/**/domain`.

## Data Source Extension Rules
New data sources should integrate through the case snapshot and personalization layers.

Preferred sequence:
1. define or extend feature/domain contracts
2. add platform adapter or ingestion service
3. expose the signal in `CaseSnapshot` (features/companion/core)
4. consume it in personalization, engagement, digest, or impact logic
5. add validation and docs

## High-Risk Files
- `src/care_pilot/config/settings.py`
- `src/care_pilot/platform/persistence/*`
- `src/care_pilot/platform/auth/*`
- `apps/api/carepilot_api/deps.py`
- `apps/api/carepilot_api/policy.py`
- `apps/workers/run.py`
- `README.md`
- `ARCHITECTURE.md`
- `SYSTEM_ROADMAP.md`

## Validation Matrix
Backend:
```bash
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run ruff check .
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run ty check . --extra-search-path src --output-format concise
SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest -q
```

Web:
```bash
pnpm web:lint
pnpm web:typecheck
pnpm web:build
```

Full stack:
```bash
uv run python scripts/cli.py test backend
uv run python scripts/cli.py test web
uv run python scripts/cli.py test comprehensive
```

## Definition of Done
- Scope is complete and coherent.
- Required validation has been run.
- Public interface changes are documented.
- Companion-facing changes improve patient, clinician, or impact behavior explicitly.
- No new business logic is hidden in routes or UI glue.

## Rollback and Risk Notes
- Prefer additive migrations inside the modular monolith before deleting reused v1 logic.
- Document breaking changes clearly because compatibility is not a design constraint in this stage.
- If a change weakens safety, observability, or clinician signal quality, stop and escalate.
