# Documentation Index

This directory contains focused documentation that supplements the three root canonical docs:
- `README.md`
- `ARCHITECTURE.md`
- `SYSTEM_ROADMAP.md`

## Core contributor docs
- `docs/developer-guide.md`
- `docs/operations-runbook.md`
- `docs/user-manual.md`
- `docs/config-reference.md`
- `docs/workflows.md` — orchestration standard (LangGraph)

## API contracts and policy
- `docs/api/auth.md`
- `docs/api/emotions.md`
- `docs/api/recommendation-agent.md`
- `docs/api/suggestions.md`
- `docs/api/rbac.md`

## Architecture deep-dives
- `docs/architecture/emotion-pipeline.md`
- `docs/architecture/meal-analysis.md`
- `docs/architecture/agent-layer-reference.md`
- `docs/architecture/event-driven/ARCHITECTURE.md` — event timeline + workflows + agents alignment pack
- `docs/architecture/event-driven/event-coverage.md` — workflow event timeline coverage map
- `docs/plans/2026-03-14-agent-layer-audit-refactor-spec.md` — agent layer boundaries + checklist

## Feature-specific notes
- `docs/features/food-normalization.md`

Runtime API discovery:
- FastAPI interactive docs: `http://localhost:8001/docs`
- Route definitions under `apps/api/carepilot_api/routers/` remain the code-level source of truth for current endpoints

## Supporting assets
- `docs/architecture/architecture.drawio`
- `docs/architecture/system-interaction-flow.drawio`
- `docs/architecture/meal-analysis-architecture.drawio`
- `docs/architecture/target-system-architecture.drawio`

## Maintenance rule
Keep this index small. If a document mostly repeats architecture, roadmap, or contributor workflow content, fold that content back into the canonical files instead of adding another overview doc.
