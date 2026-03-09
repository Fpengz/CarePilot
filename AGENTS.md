# Agent Workflow Contract

## Purpose
This file defines how human contributors and AI agents should collaborate on the companion architecture in this repository.

It supplements:
- `CONTRIBUTING.md`
- `ARCHITECTURE.md`
- `SYSTEM_ROADMAP.md`

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

## Architecture Ownership Map
- Transport/API: `apps/api/dietary_api/**`
- Web UX: `apps/web/**`
- Worker/runtime: `apps/workers/**`
- Domain contracts: `src/dietary_guardian/domain/**`
- Application use cases: `src/dietary_guardian/application/**`
- Infrastructure adapters: `src/dietary_guardian/infrastructure/**`
- Legacy reusable services: `src/dietary_guardian/services/**`
- Documentation: `README.md`, `ARCHITECTURE.md`, `SYSTEM_ROADMAP.md`, `docs/**`

## Canonical Companion Modules
Changes that affect patient guidance, clinician summaries, or impact tracking should prefer these modules:
- `application/case_snapshot`
- `application/personalization`
- `application/engagement`
- `application/care_plans`
- `application/clinician_digest`
- `application/impact`
- `application/interactions`

Do not put new business logic primarily in route handlers.

## Agent Design Rules
- Default to deterministic logic before adding an agent.
- Add a new agent only when specialization materially improves reasoning quality.
- Agents must use typed input/output contracts.
- Agents must not write durable state directly.
- Safety and policy checks remain outside prompts.

## Data Source Extension Rules
New data sources should integrate through the case snapshot and personalization layers.

Preferred sequence:
1. define or extend domain contracts
2. add infrastructure adapter or ingestion service
3. expose the signal in `CaseSnapshot`
4. consume it in personalization, engagement, digest, or impact logic
5. add validation and docs

## High-Risk Files
- `src/dietary_guardian/config/settings.py`
- `src/dietary_guardian/infrastructure/persistence/*`
- `src/dietary_guardian/infrastructure/auth/*`
- `apps/api/dietary_api/deps.py`
- `apps/api/dietary_api/policy.py`
- `apps/workers/run.py`
- `README.md`
- `ARCHITECTURE.md`
- `SYSTEM_ROADMAP.md`

## Validation Matrix
Backend:
```bash
uv run ruff check .
uv run ty check . --extra-search-path src --output-format concise
uv run pytest -q
```

Web:
```bash
pnpm web:lint
pnpm web:typecheck
pnpm web:build
```

Full stack:
```bash
uv run python scripts/dg.py test backend
uv run python scripts/dg.py test web
uv run python scripts/dg.py test comprehensive
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
