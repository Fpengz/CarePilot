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

## Auth and policy references
- `docs/api-auth-contract.md`
- `docs/rbac-matrix.md`

## Focused subsystem notes
- `docs/meal-analysis-agents.md`

## Product and pitch notes
- `docs/hackathon-answer.md`
  This is judge-facing and narrative-focused. It is not the canonical engineering source of truth.

## API contract references
- `docs/api-emotions-contract.md`
- `docs/api-recommendation-agent-contract.md`
- `docs/api-suggestions-contract.md`
- `docs/api-auth-contract.md`

Runtime API discovery:
- FastAPI interactive docs: `http://localhost:8001/docs`
- Route definitions under `apps/api/dietary_api/routers/` remain the code-level source of truth for current endpoints

## Supporting assets
- `docs/architecture/target-system-architecture.drawio`

## Maintenance rule
Keep this index small. If a document mostly repeats architecture, roadmap, or contributor workflow content, fold that content back into the canonical files instead of adding another overview doc.
