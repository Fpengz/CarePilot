# Agent Workflow Contract

## Purpose
This file defines how AI agents should collaborate in this repository.
It supplements, and does not replace, [CONTRIBUTING.md](./CONTRIBUTING.md).

## Precedence
- Product and architecture standards: `CONTRIBUTING.md`, `ARCHITECTURE.md`
- Agent collaboration and task isolation: `AGENTS.md`
- Branch and merge operations: `docs/branching-strategy.md`

## Roles
- Planner: defines decision-complete scope, interfaces, validation, and rollout.
- Implementer: executes approved scope only and keeps changes minimal.
- Reviewer: validates correctness, safety, regressions, and boundary hygiene.

## Task Contract
Every multi-agent task must include:
- Goal: what outcome is required.
- Scope: in-scope and out-of-scope behavior.
- Files: owned files and shared files expected to change.
- Validation: exact commands and expected outcomes.
- Risk: user impact, migration/compat implications, and rollback approach.

## Branching and Isolation
- Use short-lived task branches from `main`.
- Recommended branch names:
  - `feat/<topic>`
  - `fix/<topic>`
  - `docs/<topic>`
  - `refactor/<topic>`
  - `agent/<task-name>`
- One coherent change per PR.
- Avoid mixing unrelated refactors with feature or bugfix work.

## Ownership Map
- Backend API: `apps/api/dietary_api/**`
- Shared backend core: `src/dietary_guardian/**`
- Worker runtime: `apps/workers/**`
- Frontend: `apps/web/**`
- Tests: `tests/**`, `apps/api/tests/**`, `apps/web/e2e/**`
- Documentation: `docs/**`, `README.md`, `CONTRIBUTING.md`, `AGENTS.md`

## High-Risk Files (Coordinator Review Required)
- `.github/workflows/*`
- `pyproject.toml`
- `package.json`
- `pnpm-lock.yaml`
- `Dockerfile`
- `compose.dev.yml`
- `.env.example`
- `src/dietary_guardian/config/settings.py`
- `src/dietary_guardian/infrastructure/persistence/*`
- `src/dietary_guardian/infrastructure/auth/*`
- `src/dietary_guardian/application/auth/*`
- `apps/api/dietary_api/policy.py`
- `apps/api/dietary_api/deps.py`

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

## PR Requirements
- Use the repository PR template.
- Include changed files and affected layers.
- Include executed validation commands and outcomes.
- Include risk and rollback notes.
- Keep diffs scoped and reviewable.

## Conflict Handling
- If two branches modify the same high-risk file, merge the lower-risk branch first.
- Rebase feature branches after high-risk merges.
- Re-run full validation after conflict resolution.

## Definition of Done
- Scope complete and behavior matches task contract.
- Required validation commands pass.
- No undocumented interface change.
- Risk and rollback documented in PR.
- Reviewer confirms no obvious regressions.

## Final Escalation Rule
If required behavior conflicts with `CONTRIBUTING.md` or production safety constraints,
stop and escalate to maintainers before implementation.
