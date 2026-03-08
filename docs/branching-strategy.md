# Branching Strategy

## Purpose
Defines practical branching and merge sequencing for parallel human/agent work in this monorepo.

## Principles
- Keep branches short-lived and task-scoped.
- Merge low-risk isolated work first.
- Sequence high-risk shared-file changes with explicit owner review.
- Rebase often to minimize integration drift.

## Branch Types
- `feat/<topic>`: new capabilities.
- `fix/<topic>`: bug fixes.
- `docs/<topic>`: documentation only.
- `refactor/<topic>`: behavior-preserving restructures.
- `agent/<task-name>`: multi-agent execution branch.

## Recommended Workflow
1. Sync local `main` and branch from latest head.
2. Implement a single coherent scope.
3. Run required validation commands.
4. Open PR using repository template.
5. Resolve review comments without widening scope.
6. Rebase before merge if `main` moved.

## Merge Order Guidance
Low-risk first:
- docs-only updates
- leaf-module refactors
- isolated frontend or API route fixes

High-risk later:
- auth/session changes
- persistence schema/adapter changes
- workflow/runtime policy changes
- CI/workflow pipeline changes

## Shared File Coordination
Treat these as coordinator-controlled merge points:
- `.github/workflows/*`
- `pyproject.toml`, `package.json`, `pnpm-lock.yaml`
- `src/dietary_guardian/config/settings.py`
- `src/dietary_guardian/infrastructure/persistence/*`
- `src/dietary_guardian/infrastructure/auth/*`
- `apps/api/dietary_api/policy.py`, `apps/api/dietary_api/deps.py`

## Validation Expectations
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

Comprehensive:
```bash
uv run python scripts/dg.py test comprehensive
```

## Rebase and Conflict Rules
- Rebase against `main` before requesting final review.
- If conflicts involve high-risk shared files, pause and coordinate owner review.
- After conflict resolution, rerun backend + web validation for impacted areas.

## Branch Protection Checklist (GitHub Settings)
- Protect `main`.
- Require pull requests before merge.
- Require status checks to pass.
- Require up-to-date branch before merge.
- Require CODEOWNERS review for protected paths.
