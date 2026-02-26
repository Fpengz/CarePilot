# API Index

This repository's API surface is documented incrementally. This file is the root index for API contracts and endpoint guides.

## Canonical Sources
- FastAPI interactive docs (runtime): `http://localhost:8001/docs`
- `apps/api/dietary_api/routers/` — route definitions (source of truth for current endpoints)

## Contract Docs
- `docs/api-auth-contract.md` — auth/session payloads and migration notes
- `docs/api-suggestions-contract.md` — unified report-to-suggestion flow and persistence

## Current Endpoint Areas (v1)
- Auth: login, signup, logout, me, profile, password, sessions, audit events
- Meals: analyze, records
- Reports / Recommendations: parse, generate
- Reminders
- Alerts
- Workflows
- Notifications
- Households: create/current/members/invite/join/leave/remove/rename/active

## Planned Contract Docs
- `docs/meal-analysis-contract.md` (meal typed summary + workflow semantics)
