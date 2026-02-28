# Product Roadmap (Now / Next / Later)

## Goal
Operate Dietary Guardian as a production-grade, web-first health assistant platform with:
- robust account + household management
- reliable meal/report/recommendation workflows
- adaptive meal personalization that improves with user behavior over time
- policy-driven access control
- traceable observability and deployment readiness

## Delivery Assumptions
- Single-node deployment baseline
- SQLite-backed persistence (v1 production-ish default)
- Web-first UX (`apps/web`) as primary surface
- Streamlit remains internal/demo tooling
- Continual learning baseline is online reranking + persisted preference snapshots; offline retraining remains a next-step capability

## Status Legend
- `**[Complete]**` Delivered and validated through tests/checks.
- `**[In Progress]**` Active implementation in current cycle.
- `**[Planned]**` Scoped and prioritized, not started.
- `**[Blocked]**` Waiting on dependency/decision.

## Now (0–4 Weeks)

### `**[Complete]**` Account, Session, and Household Foundations
- **Outcome:** Users can signup/login, manage profile/password/sessions, and manage household membership with owner/member role rules.
- **Impact:** Establishes secure identity and collaboration primitives needed for all health workflows.
- **Done criteria:**
  - Auth API + web flows are operational (signup/login/logout/me/profile/password/sessions/audit).
  - Household create/invite/join/leave/remove/member-list flows are operational.
  - SQLite-backed auth/session persistence is enabled by default.

### `**[Complete]**` Meal and Suggestions Core Workflow
- **Outcome:** Meal analysis, report parsing, recommendation generation, and suggestion persistence are integrated end-to-end.
- **Impact:** Users can move from input to actionable health guidance in a single product surface.
- **Done criteria:**
  - Typed meal summary contract and meal record pagination are available.
  - Suggestions orchestration (`generate-from-report`) and persisted history are available.
  - Household-scoped visibility for suggestions is enforced with access controls.

### `**[Complete]**` Adaptive Meal Recommendation Agent
- **Outcome:** The platform can use persisted health profiles, meal history, biomarkers, and user feedback to rank daily meal recommendations and healthier substitutions.
- **Impact:** Users receive more realistic, localized recommendations that trade off health improvement against adherence and taste similarity instead of getting only static rule-driven guidance.
- **Done criteria:**
  - Health profiles persist age, locale, BMI inputs, nutrition limits, calorie targets, macro focus, restrictions, and cuisine preferences.
  - `GET /api/v1/recommendations/daily-agent`, `POST /api/v1/recommendations/substitutions`, and `POST /api/v1/recommendations/interactions` are available.
  - Online preference learning updates future ranking after accept/dismiss/swap events, with deterministic fallback preserved for cold-start users.

### `**[Complete]**` Policy, Observability, and Error Semantics Hardening
- **Outcome:** API access and failure semantics are centralized with request/correlation trace propagation across workflows.
- **Impact:** Reduces authorization drift and improves triage/debug capability in production.
- **Done criteria:**
  - Action-based policy checks are enforced in routes.
  - Standard error envelope + centralized handlers are used consistently.
  - Request/correlation IDs propagate through API responses, workflow payloads, and logs.

### `**[Complete]**` UI/UX Stabilization + Smoke Coverage
- **Outcome:** Core web journeys are polished for mobile/a11y and validated by e2e smoke tests.
- **Impact:** Improves user trust and lowers regression risk for primary workflows.
- **Done criteria:**
  - Dashboard/suggestions/meals views use typed state rendering over debug-first JSON.
  - Mobile header/sidebar/dialog interactions are accessible and usable.
  - Playwright smoke tests cover login redirect, mobile navigation behavior, and the adaptive dashboard recommendation surface.

## Next (Following 1–2 Cycles)

### `**[Planned]**` Offline Learning Refresh and Catalog Operations
- **Outcome:** Add scheduled refresh of user preference state and manage the localized meal catalog as an operational dataset.
- **Impact:** Improves recommendation quality beyond online reranking while keeping inference behavior explainable and stable.
- **Done criteria:**
  - Offline refresh job rebuilds preference snapshots and derived features from historical logs and interactions.
  - Meal catalog growth, review, and localization updates are documented and testable.
  - Recommendation diagnostics expose why candidate ranking changed after model/catalog refreshes.

### `**[Planned]**` Environment Profiles and Secret Hygiene
- **Outcome:** Introduce explicit environment profiles and hardened secret management for deployment tiers.
- **Impact:** Improves operational safety and reduces configuration drift.
- **Done criteria:**
  - Profiled env strategy (`development/staging/production`) is documented and enforced.
  - Deployment-time secret validation and rotation guidance are in place.

### `**[Planned]**` CI/Validation Parity and Coverage Maturity
- **Outcome:** Align local and CI gates to enforce consistent quality thresholds.
- **Impact:** Reduces “works locally, fails in CI” friction and improves release confidence.
- **Done criteria:**
  - Shared validation entrypoints are used in both local and CI.
  - Coverage target and test matrix are tightened with explicit ownership.

### `**[Planned]**` Runtime Readiness and Diagnostic Surfaces
- **Outcome:** Add richer readiness diagnostics for inference/provider/runtime dependencies.
- **Impact:** Faster incident detection and clearer operational visibility.
- **Done criteria:**
  - Expanded readiness signal beyond liveness.
  - Provider/runtime health diagnostics documented and exposed.

## Later (Beyond Next)

### `**[Planned]**` Policy-Driven Feature Flag Platform
- **Outcome:** Introduce typed feature-flag controls integrated with policy/access boundaries.
- **Impact:** Safe incremental rollouts and controlled experimentation.
- **Done criteria:**
  - Feature flags are schema-validated and environment-aware.
  - Policy layer can gate feature availability by role/scope/context.

### `**[Planned]**` Advanced Config Telemetry
- **Outcome:** Add structured config telemetry for startup/runtime introspection.
- **Impact:** Improves debugging and compliance traceability in production.
- **Done criteria:**
  - Config provenance and effective runtime values are auditable.
  - Sensitive fields are redacted by default across telemetry outputs.
