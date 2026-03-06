> [!WARNING]
> Historical archive only. Content may be outdated.
> Canonical docs: `README.md`, `docs/roadmap-v1.md`, `docs/feature-audit.md`, `docs/config-reference.md`.

> Historical snapshot archived from live docs.
> Canonical current audit: `docs/feature-audit.md`.

# Feature Capability Audit — 2026-03-05

## Executive Summary
All five audited capabilities are implemented end-to-end in this repository with API routes, service logic, persistence, frontend surfaces, and automated tests. The previously partial area (symptom check-ins tied into reports) is now wired through `POST /api/v1/reports/parse` and exposed on `/reports`, with workflow timeline visibility through `/api/v1/workflows/{correlation_id}`.

### Top Gaps
- Dedicated report workflow execution still emits directly through `event_timeline` rather than a first-class `WorkflowCoordinator` method.
- `src/dietary_guardian/models/role_tools.py` is still absent (tool-policy modeling currently uses `models/tooling.py` and `models/profile_tools.py`).
- Environmental monitoring and demographic-context personalization remain research-track features (outside this audit scope).
- CI-hosted Postgres/Redis integration coverage is still less comprehensive than local compose-backed validation.

## Feature Audit Table

| Feature | Status | Evidence (paths + symbols/routes + tests) | Missing Pieces | Recommended Integration Points |
|---|---|---|---|---|
| A) Patient → Doctor Clinical Card Generation | ✅ | Routes: `apps/api/dietary_api/routers/clinical_cards.py` (`clinical_cards_generate/list/get`); Service: `apps/api/dietary_api/services/clinical_cards.py` (`generate_clinical_card_for_session`) with aggregation, deltas, SOAP-like sections, trends; Model: `src/dietary_guardian/models/clinical_card.py`; Storage: `clinical_cards` in `src/dietary_guardian/infrastructure/persistence/postgres_schema.py`; Frontend: `apps/web/app/clinical-cards/page.tsx`; Tests: `apps/api/tests/test_api_clinical_cards.py`. | None | N/A |
| B) Medication Tracking + Metrics | ✅ | Routes: `apps/api/dietary_api/routers/medications.py`; Services: `apps/api/dietary_api/services/medications.py`, `src/dietary_guardian/services/medication_service.py`, `src/dietary_guardian/services/reminder_scheduler.py`; Worker: `apps/workers/run.py`; Storage: `medication_regimens`, `medication_adherence_events` in Postgres schema; Frontend: `apps/web/app/medications/page.tsx`, `apps/web/app/reminders/page.tsx`; Tests: `apps/api/tests/test_api_medications.py`, `tests/test_medication_scheduler.py`, `tests/test_mcr_metrics.py`, `tests/test_reminder_scheduler.py`. | None | N/A |
| C) Diet Pattern Analysis (Weekly) | ✅ | Routes: `apps/api/dietary_api/routers/meals.py` (`/api/v1/meal/analyze`, `/api/v1/meal/weekly-summary`); Services: `apps/api/dietary_api/services/meals.py`, `src/dietary_guardian/services/weekly_nutrition_service.py`; Storage: `meal_records`; Frontend: `apps/web/app/meals/page.tsx`; Tests: `apps/api/tests/test_api_meal_weekly.py`. | None | N/A |
| D) Symptom Check-ins | ✅ | Routes: `apps/api/dietary_api/routers/symptoms.py`; Service: `apps/api/dietary_api/services/symptoms.py`; Storage: `symptom_checkins`; Reports integration: `apps/api/dietary_api/services/reports.py` returns `symptom_summary` + `symptom_window`; Frontend: `apps/web/app/symptoms/page.tsx`, `apps/web/app/reports/page.tsx`; Tests: `apps/api/tests/test_api_symptoms.py`, `apps/api/tests/test_api_reports_and_recommendations.py::test_reports_parse_includes_symptom_summary_and_workflow_trace`. | None | N/A |
| E) Numerical Data Change Analysis | ✅ | Route: `apps/api/dietary_api/routers/metrics.py`; Service: `apps/api/dietary_api/services/metrics.py`; Deterministic compute: `src/dietary_guardian/services/metrics_trend_service.py`; Model: `src/dietary_guardian/models/metrics_trend.py`; Frontend: `apps/web/app/metrics/page.tsx`; Tests: `apps/api/tests/test_api_metrics_trends.py`. | None | N/A |

## Evidence Appendix

### A) Clinical Cards
- `apps/api/dietary_api/routers/clinical_cards.py` mounts generate/list/get routes.
- `apps/api/dietary_api/services/clinical_cards.py` builds sections (`subjective`, `objective`, `assessment`, `plan`) and computes deltas/trends.
- `src/dietary_guardian/infrastructure/persistence/postgres_schema.py` defines `clinical_cards` table and index.
- `apps/web/app/clinical-cards/page.tsx` calls generate/list/get and renders section/trend payloads.
- `apps/api/tests/test_api_clinical_cards.py` verifies generation, listing, and retrieval.

### B) Medication + Metrics
- `apps/api/dietary_api/routers/medications.py` exposes regimen and adherence endpoints.
- `apps/api/dietary_api/services/medications.py` records adherence and computes totals/adherence rate.
- `src/dietary_guardian/services/medication_service.py` computes schedule timing and MCR metrics.
- `src/dietary_guardian/services/reminder_scheduler.py` dispatches due scheduled notifications.
- `apps/workers/run.py` runs scheduler + outbox worker under coordination locks.
- Tests: `apps/api/tests/test_api_medications.py`, `tests/test_medication_scheduler.py`, `tests/test_mcr_metrics.py`, `tests/test_reminder_scheduler.py`.

### C) Diet Pattern Analysis (Weekly)
- `apps/api/dietary_api/services/meals.py` ingests uploads, persists meal records, and serves weekly summaries.
- `src/dietary_guardian/services/weekly_nutrition_service.py` computes weekly totals, daily breakdown, and pattern flags.
- `apps/web/app/meals/page.tsx` renders weekly summary UI and pattern flags.
- `apps/api/tests/test_api_meal_weekly.py` validates weekly rollup behavior.

### D) Symptom Check-ins
- `apps/api/dietary_api/routers/symptoms.py` provides create/list/summary routes.
- `apps/api/dietary_api/services/symptoms.py` performs safety triage and aggregate summary.
- `apps/api/dietary_api/services/reports.py` now includes symptom summary and window in report parse output.
- `apps/web/app/reports/page.tsx` now renders report parse + symptom context.
- `apps/api/tests/test_api_reports_and_recommendations.py` asserts symptom summary fields and workflow trace visibility.

### E) Numerical Change Analysis
- `src/dietary_guardian/services/metrics_trend_service.py` deterministically computes `delta`, `percent_change`, `slope_per_point`, `direction`.
- `apps/api/dietary_api/services/metrics.py` builds trend responses by requested metric families.
- `apps/web/app/metrics/page.tsx` displays deterministic trend outputs.
- `apps/api/tests/test_api_metrics_trends.py` validates expected delta/direction results.

## Proposed MVP Scope
All audited features are complete. The next MVP should focus on non-audited roadmap deltas:
1. Environmental context ingestion (`air_quality`, temperature, humidity) with recommendation hooks.
2. Fairness-constrained demographic-context experimentation behind explicit policy controls.
3. First-class report workflow type in `WorkflowCoordinator` to align report events with the existing workflow runtime contract.
