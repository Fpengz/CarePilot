# Feature Capability Audit (Current)

Last updated: 2026-03-06

#### 1) Executive Summary
The repository currently shows end-to-end coverage for all five audited features (A–E) with concrete FastAPI routes, service-layer logic, domain models, persistence tables/adapters (including Postgres schema and store implementations), frontend pages/API clients, and targeted tests. Workflow replay and timeline traces are wired, and deterministic trend/delta computation is implemented in explicit compute services rather than LLM-only math. No audited feature is docs-only in the current codebase.

- Role/tool contract modeling exists in [`models/role_tools.py`](../src/dietary_guardian/models/role_tools.py) and DB-backed tool policy APIs are available; rollout still defaults to shadow enforcement mode.
- Workflow runtime contract exposure now exists at [`GET /api/v1/workflows/runtime-contract`](../apps/api/dietary_api/routers/workflows.py), backed by [`services/agent_registry.py`](../src/dietary_guardian/services/agent_registry.py).
- Redis cache/coordination now runs on v2-only keyspace naming with legacy fallback removed from runtime adapters.
- CI-level full Postgres+Redis integration proof for all A–E remains less explicit than unit/API suite coverage in-repo.

#### 2) Feature Audit Table

| Feature | Status (✅/🟡/❌) | Evidence (paths + symbols/routes + tests) | Missing Pieces (if 🟡/❌) | Recommended Integration Points (exact modules) |
|---|---|---|---|---|
| A) Patient → Doctor Clinical Card Generation | ✅ | Routes: [`clinical_cards_generate/list/get`](../apps/api/dietary_api/routers/clinical_cards.py). Service: [`generate_clinical_card_for_session`](../apps/api/dietary_api/services/clinical_cards.py) computes aggregation, window deltas, trends, sectioned SOAP-like output (`subjective/objective/assessment/plan`). Models: [`ClinicalCardRecord`](../src/dietary_guardian/models/clinical_card.py), [`MetricTrend`](../src/dietary_guardian/models/metrics_trend.py). Storage: `clinical_cards` table + store methods in [`postgres_schema.py`](../src/dietary_guardian/infrastructure/persistence/postgres_schema.py), [`save/list/get_clinical_card`](../src/dietary_guardian/infrastructure/persistence/postgres_app_store.py). Frontend: [`/clinical-cards`](../apps/web/app/clinical-cards/page.tsx). Tests: [`test_api_clinical_cards.py`](../apps/api/tests/test_api_clinical_cards.py). | None | N/A |
| B) Medication Tracking + Metrics | ✅ | Routes: regimen CRUD + adherence in [`routers/medications.py`](../apps/api/dietary_api/routers/medications.py). Services: [`services/medications.py`](../apps/api/dietary_api/services/medications.py), [`compute_mcr/generate_daily_reminders`](../src/dietary_guardian/services/medication_service.py), scheduler loop/once in [`reminder_scheduler.py`](../src/dietary_guardian/services/reminder_scheduler.py). Worker orchestration in [`apps/workers/run.py`](../apps/workers/run.py). Storage: `medication_regimens`, `medication_adherence_events`, `reminder_events` in [`postgres_schema.py`](../src/dietary_guardian/infrastructure/persistence/postgres_schema.py) + adapter methods in [`postgres_app_store.py`](../src/dietary_guardian/infrastructure/persistence/postgres_app_store.py). Frontend: [`/medications`](../apps/web/app/medications/page.tsx), [`/reminders`](../apps/web/app/reminders/page.tsx). Tests: [`test_api_medications.py`](../apps/api/tests/test_api_medications.py), [`test_mcr_metrics.py`](../tests/test_mcr_metrics.py), [`test_reminder_scheduler.py`](../tests/test_reminder_scheduler.py). | None | N/A |
| C) Diet Pattern Analysis (Weekly) | ✅ | Meal ingestion route [`POST /api/v1/meal/analyze`](../apps/api/dietary_api/routers/meals.py) and service [`analyze_meal`](../apps/api/dietary_api/services/meals.py). Persistent meal logs: `meal_records` table and store methods [`save/list/get_meal_record`](../src/dietary_guardian/infrastructure/persistence/postgres_app_store.py). Weekly rollup/pattern detection in [`build_weekly_nutrition_summary`](../src/dietary_guardian/services/weekly_nutrition_service.py) surfaced via [`GET /api/v1/meal/weekly-summary`](../apps/api/dietary_api/routers/meals.py). Frontend: [`/meals`](../apps/web/app/meals/page.tsx). Tests: [`test_api_meal_weekly.py`](../apps/api/tests/test_api_meal_weekly.py). | None | N/A |
| D) Symptom Check-ins | ✅ | Routes: create/list/summary in [`routers/symptoms.py`](../apps/api/dietary_api/routers/symptoms.py). Service: triage + persistence + summarization in [`services/symptoms.py`](../apps/api/dietary_api/services/symptoms.py). Models: [`SymptomCheckIn/SymptomSummary`](../src/dietary_guardian/models/symptom.py). Storage: `symptom_checkins` table/index in [`postgres_schema.py`](../src/dietary_guardian/infrastructure/persistence/postgres_schema.py), adapter methods in [`postgres_app_store.py`](../src/dietary_guardian/infrastructure/persistence/postgres_app_store.py). Report linkage: [`parse_report_for_session`](../apps/api/dietary_api/services/reports.py) returns `symptom_summary` and `symptom_window`. Frontend: [`/symptoms`](../apps/web/app/symptoms/page.tsx), [`/reports`](../apps/web/app/reports/page.tsx). Tests: [`test_api_symptoms.py`](../apps/api/tests/test_api_symptoms.py), [`test_api_reports_and_recommendations.py`](../apps/api/tests/test_api_reports_and_recommendations.py). | None | N/A |
| E) Numerical Data Change Analysis | ✅ | Deterministic compute service in [`metrics_trend_service.py`](../src/dietary_guardian/services/metrics_trend_service.py) (`build_metric_trend` computes `delta`, `percent_change`, `slope_per_point`, `direction`). API route [`GET /api/v1/metrics/trends`](../apps/api/dietary_api/routers/metrics.py) and service wiring in [`services/metrics.py`](../apps/api/dietary_api/services/metrics.py). Model contracts in [`models/metrics_trend.py`](../src/dietary_guardian/models/metrics_trend.py). Frontend: [`/metrics`](../apps/web/app/metrics/page.tsx). Tests: [`test_api_metrics_trends.py`](../apps/api/tests/test_api_metrics_trends.py). | None | N/A |

#### 3) Evidence Appendix

### A) Patient → Doctor Clinical Card Generation
- [`apps/api/dietary_api/routers/clinical_cards.py`](../apps/api/dietary_api/routers/clinical_cards.py): `clinical_cards_generate`, `clinical_cards_list`, `clinical_cards_get` route handlers.
- [`apps/api/dietary_api/services/clinical_cards.py`](../apps/api/dietary_api/services/clinical_cards.py): builds `sections` with `subjective/objective/assessment/plan`.
- [`apps/api/dietary_api/services/clinical_cards.py`](../apps/api/dietary_api/services/clinical_cards.py): computes `deltas` and `trends` via `build_metric_trend`.
- [`src/dietary_guardian/models/clinical_card.py`](../src/dietary_guardian/models/clinical_card.py): clinical-card contract includes `sections`, `deltas`, `trends`.
- [`src/dietary_guardian/infrastructure/persistence/postgres_schema.py`](../src/dietary_guardian/infrastructure/persistence/postgres_schema.py): `clinical_cards` table + index.
- [`src/dietary_guardian/infrastructure/persistence/postgres_app_store.py`](../src/dietary_guardian/infrastructure/persistence/postgres_app_store.py): `save_clinical_card`, `list_clinical_cards`, `get_clinical_card`.
- [`apps/web/app/clinical-cards/page.tsx`](../apps/web/app/clinical-cards/page.tsx): generate/list/get flows and trend rendering.
- [`apps/api/tests/test_api_clinical_cards.py`](../apps/api/tests/test_api_clinical_cards.py): verifies create/list/get and section keys.

### B) Medication Tracking + Metrics
- [`apps/api/dietary_api/routers/medications.py`](../apps/api/dietary_api/routers/medications.py): regimen CRUD + adherence endpoints.
- [`apps/api/dietary_api/services/medications.py`](../apps/api/dietary_api/services/medications.py): adherence capture and totals/adherence-rate calculation.
- [`src/dietary_guardian/services/medication_service.py`](../src/dietary_guardian/services/medication_service.py): reminder generation and `compute_mcr`.
- [`src/dietary_guardian/services/reminder_scheduler.py`](../src/dietary_guardian/services/reminder_scheduler.py): scheduled dispatch+delivery loop.
- [`apps/workers/run.py`](../apps/workers/run.py): worker lock orchestration for scheduler/outbox.
- [`src/dietary_guardian/infrastructure/persistence/postgres_schema.py`](../src/dietary_guardian/infrastructure/persistence/postgres_schema.py): `medication_regimens`, `medication_adherence_events`, `reminder_events`.
- [`src/dietary_guardian/infrastructure/persistence/postgres_app_store.py`](../src/dietary_guardian/infrastructure/persistence/postgres_app_store.py): regimen/adherence persistence APIs.
- [`apps/api/tests/test_api_medications.py`](../apps/api/tests/test_api_medications.py): regimen CRUD + adherence metrics + reminder generation from persisted regimen.
- [`tests/test_mcr_metrics.py`](../tests/test_mcr_metrics.py): MCR/evaluation metric computations.
- [`tests/test_reminder_scheduler.py`](../tests/test_reminder_scheduler.py): scheduler dispatch/delivery behavior.

### C) Diet Pattern Analysis (Weekly)
- [`apps/api/dietary_api/routers/meals.py`](../apps/api/dietary_api/routers/meals.py): `meal_analyze`, `meal_records`, `meal_daily_summary`, `meal_weekly_summary`.
- [`apps/api/dietary_api/services/meals.py`](../apps/api/dietary_api/services/meals.py): upload ingestion + persistence + weekly summary call.
- [`src/dietary_guardian/services/weekly_nutrition_service.py`](../src/dietary_guardian/services/weekly_nutrition_service.py): weekly totals, daily breakdown, pattern flags.
- [`src/dietary_guardian/infrastructure/persistence/postgres_schema.py`](../src/dietary_guardian/infrastructure/persistence/postgres_schema.py): `meal_records` table and user-time index.
- [`src/dietary_guardian/infrastructure/persistence/postgres_app_store.py`](../src/dietary_guardian/infrastructure/persistence/postgres_app_store.py): `save_meal_record`/`list_meal_records`.
- [`apps/web/app/meals/page.tsx`](../apps/web/app/meals/page.tsx): meal upload, daily/weekly summary surfaces.
- [`apps/api/tests/test_api_meal_weekly.py`](../apps/api/tests/test_api_meal_weekly.py): weekly rollup contract assertions.

### D) Symptom Check-ins
- [`apps/api/dietary_api/routers/symptoms.py`](../apps/api/dietary_api/routers/symptoms.py): check-in create/list/summary endpoints.
- [`apps/api/dietary_api/services/symptoms.py`](../apps/api/dietary_api/services/symptoms.py): triage (`evaluate_text_safety`), persistence, aggregate summary.
- [`src/dietary_guardian/models/symptom.py`](../src/dietary_guardian/models/symptom.py): symptom models/contracts.
- [`src/dietary_guardian/infrastructure/persistence/postgres_schema.py`](../src/dietary_guardian/infrastructure/persistence/postgres_schema.py): `symptom_checkins` table.
- [`src/dietary_guardian/infrastructure/persistence/postgres_app_store.py`](../src/dietary_guardian/infrastructure/persistence/postgres_app_store.py): `save_symptom_checkin` + `list_symptom_checkins`.
- [`apps/api/dietary_api/services/reports.py`](../apps/api/dietary_api/services/reports.py): report parse includes `symptom_summary` + `symptom_window`.
- [`apps/web/app/symptoms/page.tsx`](../apps/web/app/symptoms/page.tsx): check-in tool and summary retrieval UI.
- [`apps/web/app/reports/page.tsx`](../apps/web/app/reports/page.tsx): symptom-context report surface.
- [`apps/api/tests/test_api_symptoms.py`](../apps/api/tests/test_api_symptoms.py): create/list/summary + red-flag counting.
- [`apps/api/tests/test_api_reports_and_recommendations.py`](../apps/api/tests/test_api_reports_and_recommendations.py): symptom summary in reports + workflow trace evidence.

### E) Numerical Data Change Analysis
- [`apps/api/dietary_api/routers/metrics.py`](../apps/api/dietary_api/routers/metrics.py): `GET /api/v1/metrics/trends`.
- [`apps/api/dietary_api/services/metrics.py`](../apps/api/dietary_api/services/metrics.py): assembles metric families and calls deterministic trend builder.
- [`src/dietary_guardian/services/metrics_trend_service.py`](../src/dietary_guardian/services/metrics_trend_service.py): deterministic `delta`, `percent_change`, `slope_per_point`, `direction`.
- [`src/dietary_guardian/models/metrics_trend.py`](../src/dietary_guardian/models/metrics_trend.py): trend contracts.
- [`apps/web/app/metrics/page.tsx`](../apps/web/app/metrics/page.tsx): trend display for nutrition/adherence/biomarkers.
- [`apps/api/tests/test_api_metrics_trends.py`](../apps/api/tests/test_api_metrics_trends.py): expected delta/direction assertions.

### Investigation Step Notes (Required Files)
- Router registration confirmed in [`apps/api/dietary_api/main.py`](../apps/api/dietary_api/main.py) and [`apps/api/dietary_api/routers/__init__.py`](../apps/api/dietary_api/routers/__init__.py).
- Workflow engine confirmed in [`apps/api/dietary_api/routers/workflows.py`](../apps/api/dietary_api/routers/workflows.py), [`apps/api/dietary_api/services/workflows.py`](../apps/api/dietary_api/services/workflows.py), [`src/dietary_guardian/services/workflow_coordinator.py`](../src/dietary_guardian/services/workflow_coordinator.py).
- Data persistence confirmed in [`src/dietary_guardian/infrastructure/persistence/postgres_schema.py`](../src/dietary_guardian/infrastructure/persistence/postgres_schema.py), [`src/dietary_guardian/infrastructure/persistence/postgres_app_store.py`](../src/dietary_guardian/infrastructure/persistence/postgres_app_store.py), [`src/dietary_guardian/infrastructure/cache/redis_store.py`](../src/dietary_guardian/infrastructure/cache/redis_store.py).
- Tooling support confirmed in [`src/dietary_guardian/services/tool_registry.py`](../src/dietary_guardian/services/tool_registry.py), [`src/dietary_guardian/models/tooling.py`](../src/dietary_guardian/models/tooling.py), [`src/dietary_guardian/services/platform_tools.py`](../src/dietary_guardian/services/platform_tools.py), and agents under [`src/dietary_guardian/agents/`](../src/dietary_guardian/agents).
- Role/tools contract model confirmed in [`src/dietary_guardian/models/role_tools.py`](../src/dietary_guardian/models/role_tools.py), with runtime registry wiring in [`src/dietary_guardian/services/agent_registry.py`](../src/dietary_guardian/services/agent_registry.py) and API exposure in [`apps/api/dietary_api/routers/workflows.py`](../apps/api/dietary_api/routers/workflows.py).

## Top Gaps
- Tool-policy enforcement is intentionally `shadow` by default; production rollout to hard-enforcement remains pending.

## Proposed MVP Scope
- Keep A–E capabilities at maintenance level (no new feature build required for audit scope).
- Complete production rollout steps for policy enforcement mode transition (`shadow` -> `enforce`) and validate in staging.
- Keep Redis keyspace migration utility as operational-only maintenance tooling for legacy environments.

## One-Page Integration Plan (No Code)

### Where missing pieces would live
- Policy enforcement rollout: [`apps/api/dietary_api/policy.py`](../apps/api/dietary_api/policy.py), [`apps/api/dietary_api/services/workflows.py`](../apps/api/dietary_api/services/workflows.py), [`src/dietary_guardian/services/policy_service.py`](../src/dietary_guardian/services/policy_service.py).

### Existing services to extend
- Add rollout controls to transition from shadow policy mode to enforce mode by environment.
- Extend web-facing API client surfaces for policy/snapshot admin UX.

### New tables/fields required
- For A–E audited features: no mandatory new durable tables required to claim existing capability.
- Governance-focused additions:
  - `workflow_contract_snapshots` table for versioned runtime contracts and audit history. `**[Implemented]**`
  - `tool_role_policies` table for persistent role-tool controls. `**[Implemented]**`
