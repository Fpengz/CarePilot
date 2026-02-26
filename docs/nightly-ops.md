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

## Report Output
Write nightly report to:
- `reports/nightly_YYYY-MM-DD.md`

Required sections:
- `# Tonight's Milestone`
- `## Audit Summary (Before Changes)`
- `## Changes Made`
- `## Architecture Decisions`
- `## Safety/Compliance Notes`
- `## How to Run / Test`
- `## What's Next (Top 3 Priorities for Tomorrow)`

## Current Priority Order (Repo-Specific)
1. Suggestions unified flow + persistence
2. Safety layer formalization (structured red-flag + escalation enforcement)
3. Meal v1 completion (pagination/failure metadata/UX)
4. Household sharing integration in read flows
5. Observability baseline (trace IDs + structured logs)
6. Deployment readiness (CI + containers)

## Boundaries (Short Version)
- `apps/api`: transport only
- `apps/web`: UI only
- `src/dietary_guardian/application`: use-cases + workflows + ports
- `src/dietary_guardian/domain`: pure rules
- `src/dietary_guardian/infrastructure`: adapters (sqlite/providers/messaging)
- `src/dietary_guardian/safety`: safety policy and enforcement support
