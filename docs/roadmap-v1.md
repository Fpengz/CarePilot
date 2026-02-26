# V1 Product Delivery Roadmap

## Goal
Ship a working web-first v1 of Dietary Guardian with:
- signup + login
- meal analysis + meal records
- report parsing + suggestions
- reminders
- household basics (Apple Family-like group)
- polished onboarding and core UI/UX

## Delivery Assumptions
- Single-node deployment
- SQLite-backed persistence (production-ish v1)
- Web-first UX (`apps/web`)
- Streamlit remains internal/demo tooling

## Milestones

### Milestone 1 — Auth, Signup, Account Management
- Self-serve signup (`POST /api/v1/auth/signup`) and web signup flow
- Login/logout/me
- Profile update, password change, session management
- Auth audit events + admin audit viewer
- SQLite-backed auth/accounts/session persistence

### Milestone 2 — Meal Analysis (Daily Use)
- Stable meal analysis summary payload for UI
- Meal records history improvements (pagination/filtering)
- Workflow trace/failure metadata for meal analysis
- Manual-review guidance in UI

### Milestone 3 — Suggestions (Reports -> Recommendations)
- Unified suggestions flow (parse report + generate recommendation)
- Persisted suggestion history
- Household-shared suggestion visibility (read-only)

### Milestone 4 — Household Basics
- Create household
- Invite/join by code
- Owner/member roles
- Member list and leave/remove flows
- Shared visibility for meals/reminders/suggestions

### Milestone 5 — UI/UX Refinement and Stabilization
- Onboarding polish (`signup -> login -> first task`)
- Structured views replacing debug JSON-first flows
- Accessibility/mobile polish
- End-to-end smoke testing for core journeys

## Post-v1 Platform Work
- Env profile support and secrets management
- Config telemetry and diagnostics
- CI/local quality parity
- Health endpoints and readiness checks
- Policy-driven feature flags
