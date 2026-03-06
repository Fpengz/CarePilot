# Nightly Autonomous Build Runbook (V1)

## Goal
Provide a repeatable nightly engineering loop that improves the repo toward a production-ready v1 while preserving runnability and architectural boundaries.

## Nightly Loop (One Major Milestone Per Night)
1. Audit current repo state and recent changes
2. Select exactly one highest-impact milestone that fits one night
3. Implement with tests and small commits
4. Validate (backend or full-stack preset)
5. Update docs and write nightly report

## Validation Presets
- Backend-focused: `./tools/validate.sh backend-milestone`
- Full stack: `./tools/validate.sh full-stack`
- Unified maximum-coverage gate: `uv run python scripts/dg.py test comprehensive`

## Report Output
Write nightly report to:
- `reports/nightly_YYYY-MM-DD.md`

Historical nightly reports are archived under:
- `docs/archive/nightly-reports/`

Required sections:
- `# Tonight's Milestone`
- `## Audit Summary (Before Changes)`
- `## Changes Made`
- `## Architecture Decisions`
- `## Safety/Compliance Notes`
- `## How to Run / Test`
- `## What's Next (Top 3 Priorities for Tomorrow)`

## Current Priority Order (Repo-Specific)
1. Policy enforcement rollout (`TOOL_POLICY_ENFORCEMENT_MODE=shadow` -> `enforce`) with staged validation
2. Runtime-contract snapshot management UX (web visibility + compare flows)
3. Redis keyspace v2 production cutover and verification runbook execution
4. Recommendation-agent hardening and offline refresh hooks
5. Prompt orchestration standardization across agent flows
6. RAG v1 foundation and safety expansion

## Command of Record
- Nightly default validation command: `uv run python scripts/dg.py test comprehensive`
- If runtime constraints require a lighter run:
  - Backend-only: `uv run python scripts/dg.py test backend`
  - Web-only: `uv run python scripts/dg.py test web --skip-e2e`

## Boundaries (Short Version)
- `apps/api`: transport only
- `apps/web`: UI only
- `src/dietary_guardian/application`: use-cases + workflows + ports
- `src/dietary_guardian/domain`: pure rules
- `src/dietary_guardian/infrastructure`: adapters (sqlite/providers/messaging)
- `src/dietary_guardian/safety`: safety policy and enforcement support
