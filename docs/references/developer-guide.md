# Developer Guide

See also:
- `ARCHITECTURE.md`
- `docs/references/config-reference.md`

## Purpose
This guide defines how contributors should work in the CarePilot repository.

It is written for:
- backend engineers
- frontend engineers
- ML / applied AI engineers
- platform engineers
- AI agents operating on the repository

The project favors maintainability over cleverness. New contributions should make the architecture easier to extend, not merely add behavior.

## Repository Operating Model
The repository is a monorepo with:
- FastAPI backend under `apps/api`
- Next.js frontend under `apps/web`
- shared Python core under `src/care_pilot`
- tests at both API and repository levels

Current local-first default:
- SQLite for durable storage
- in-process orchestration for most workflows

Target production direction:
- SQLite remains supported for local and edge runtime
- Postgres is the relational scale path
- Redis for cache, ephemeral coordination, and async worker plumbing
- expanded worker and retrieval infrastructure

## Setup

Requirements:
- Python 3.12+
- Node.js 20+
- `uv`
- `pnpm`
- Docker for optional infra smoke paths

Install:

```bash
make install
```

Manual install:

```bash
uv sync
cd apps/web && pnpm install
cp .env.example .env
```

## Run locally

Default local stack:

```bash
uv run python scripts/cli.py dev
```

Useful variants:

```bash
uv run python scripts/cli.py dev --no-web
uv run python scripts/cli.py dev --no-api
uv run python scripts/cli.py dev --no-scheduler
```

## Repository map
- `apps/api/carepilot_api/`: FastAPI app, routers, API services, schemas
- `apps/web/`: Next.js app, components, typed API clients, e2e coverage
- `apps/workers/`: worker runtime
- `apps/inference/`: inference runtime service
- `src/care_pilot/core/`: tiny shared primitives
- `src/care_pilot/features/`: product behavior and feature entrypoints
- `src/care_pilot/agent/`: bounded model/provider logic
- `src/care_pilot/platform/`: persistence and external adapters
- `tests/`: repository tests

## Development Workflow

### Project Versioning
CarePilot follows Semantic Versioning (SemVer) and maintains a curated `CHANGELOG.md`. See the [Project Versioning Policy](../design-docs/architecture/versioning-policy.md) for details.

Use the CarePilot CLI to manage versions:

#### Check current version
```bash
uv run python scripts/cli.py version status
```

#### Increment version
```bash
uv run python scripts/cli.py version patch
uv run python scripts/cli.py version minor
uv run python scripts/cli.py version major
```

#### Set specific version
```bash
uv run python scripts/cli.py version set 1.2.3
```

### Branch Strategy
Use short-lived feature branches from `main`.

Recommended naming:
- `feat/<topic>`
- `fix/<topic>`
- `docs/<category>/<doc>`
- `refactor/<topic>`
- `agent/<task-name>` for multi-agent execution branches

### Pull Request Guidelines
Each PR should:
- focus on one coherent change set
- include tests or an explicit testing explanation
- describe behavior changes and migration risks
- identify affected layers: API, orchestration, agent, tool, data, frontend, infra

PRs are expected to use `.github/pull_request_template.md`. CI enforces required sections and checklist completion through the `pr-policy` workflow.

### Multi-Agent Workflow
When using multiple engineers/agents in parallel:
- Follow `AGENTS.md` for task contract requirements and ownership boundaries.
- Follow the branch isolation and merge sequencing rules in this document.
- Escalate changes that touch high-risk shared files listed in `AGENTS.md`.

Minimum multi-agent task contract:
- `Goal`
- `Scope`
- `Files`
- `Validation`
- `Risk`

Working rule:
- one agent or branch owns one coherent change at a time
- avoid mixing unrelated refactors with feature or bugfix work
- if repo-wide planning changes, update the canonical docs instead of creating new temporary root planning files

### Commit Message Standard
Use Conventional Commits.

Format:
- `<type>(<scope>): <subject>`

Examples:
- `feat(reminders): add scheduled notification delivery architecture`
- `fix(auth): reject corrupted sqlite session payloads`
- `docs(architecture): define target multi-agent runtime boundaries`

### Code Review Expectations
Reviewers should focus on:
- correctness
- boundary hygiene
- regression risk
- safety implications
- test coverage
- observability impact

### Merge and Rebase Rules
- Keep branches short-lived and task-scoped.
- Merge low-risk isolated changes first.
- Sequence high-risk shared-file work with explicit owner review.
- Rebase against `main` before final review when the branch has drifted.
- If conflicts touch shared infrastructure, auth, or policy files, pause and coordinate rather than guessing through the merge.

High-risk shared-file areas:
- `.github/workflows/*`
- `pyproject.toml`, `apps/web/package.json`, `apps/web/pnpm-lock.yaml`
- `src/care_pilot/config/app.py`
- `src/care_pilot/platform/persistence/*`
- `src/care_pilot/platform/auth/*`
- `apps/api/carepilot_api/policy.py`
- `apps/api/carepilot_api/deps.py`

### Planning and backlog hygiene
- `SYSTEM_ROADMAP.md` is the canonical roadmap and status document.
- Do not create new root planning files for temporary execution packets or one-off backlogs.
- If a plan is still active and generally useful, fold it into `SYSTEM_ROADMAP.md`, `ARCHITECTURE.md`, or `docs/references/developer-guide.md`.
- If a plan is task-local and temporary, keep it in the PR or issue context instead of adding another repository-level markdown file.

## Extension patterns

### Add or change an API feature
1. Update schema contracts in `src/care_pilot/core/contracts/api/` if the API shape changes.
2. Implement request handling in `apps/api/carepilot_api/services/<feature>.py`.
3. Keep the route in `apps/api/carepilot_api/routers/<feature>.py` transport-only.
4. Add or update API tests in `tests/api/`.
5. Update typed web client code in `apps/web/lib/api/` and UI consumers in `apps/web/app/`.

### Add or change core behavior
1. Prefer `src/care_pilot/features/` for new use cases and orchestration.
2. Extend feature-local contracts before wiring platform adapters.
3. Add infrastructure adapters under `src/care_pilot/platform/` only after the port or contract is clear.
4. Keep agents behind typed contracts and out of durable-state ownership.

### Add or change persistence/runtime infrastructure
1. Update backend-neutral contracts when the app layer should not know the backend.
2. Implement SQLite behavior in infrastructure persistence and keep external services optional.
3. Wire backend selection through the existing builder/dependency path.
4. Extend scripts and readiness behavior only when the operational path changes.

## Testing workflow

Recommended full gate:

```bash
uv run python scripts/cli.py test comprehensive
```

Focused gates:

```bash
uv run python scripts/cli.py test backend
uv run python scripts/cli.py test web
```

Direct gates:

```bash
uv run ruff check .
uv run ty check . --extra-search-path src --output-format concise
uv run pytest -q
cd apps/web && pnpm lint && pnpm typecheck && pnpm build
```

## Debugging workflow
1. Check readiness and environment configuration.
2. Run the narrowest affected backend or web tests first.
3. Confirm worker/runtime assumptions if the feature depends on reminders or async processing.
4. Escalate to the comprehensive gate before finalizing a cross-cutting change.

## Projection replay

Use this to rebuild materialized snapshot sections from the timeline:

```bash
uv run python scripts/cli.py projections replay --user-id <user-id> --since <iso-timestamp>
```

## Update this file when
- setup or local runtime commands change
- extension patterns change
- validation gates change materially
