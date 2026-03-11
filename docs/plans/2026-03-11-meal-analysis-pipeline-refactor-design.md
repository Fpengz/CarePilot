# Meal Analysis Pipeline Refactor (Stages 1–4)

> **Status**: Implemented (March 12, 2026).  
> **Note**: Use `docs/meal-analysis-agents.md` and `ARCHITECTURE.md` for current module paths.

## Summary
Refactor the meal-analysis pipeline into a staged, feature-first flow: multi‑modal perception (vision + dietary claims) → deterministic reconciliation with hybrid arbitration for unresolved conflicts → canonicalization → deterministic nutrition/risk derivation → layered persistence. Replace current meal endpoints with new schemas and write new data into new tables only (drop‑legacy, no backfill).

## Goals
- Implement Stages 1–4 from `meal-analysis-refactor.md`.
- Introduce canonical objects: `RawObservationBundle`, `ValidatedMealEvent`, `NutritionRiskProfile`, and a result envelope returned by the API.
- Make reconciliation deterministic-first with bounded arbitration.
- Store raw observations, validated events, and derived nutrition/risk separately.
- Replace existing meal-analysis API response schema.

## Non-Goals
- Stage 5B personalized action generation.
- Any migration/backfill of existing `meal_records`.
- Cross-feature personalization or feedback loop changes.

## Architecture (Stages 1–4)
1. **Perception (Stage 1)**
   - Vision Agent → bounded structured observations.
   - Dietary Agent → structured semantic claims from user text.
   - Context Ingestion Service → timestamp, location/vendor context, profile snapshot.
   - Output: `RawObservationBundle`.
2. **Reconciliation & Canonicalization (Stage 2)**
   - Deterministic alignment and conflict detection.
   - Hybrid arbitration (LLM) only for unresolved conflicts, with strict JSON output.
   - Canonical food mapping after reconciliation.
   - Output: `ValidatedMealEvent`.
3. **Nutrition & Risk (Stage 3)**
   - Deterministic nutrition and risk scoring with uncertainty bands.
   - Output: `NutritionRiskProfile`.
4. **Persistence (Stage 4)**
   - Persist raw observations, validated events, and derived profiles in separate tables.
   - Legacy `meal_records` are not written for new flows.

## Data Objects
- `RawObservationBundle`
- `ValidatedMealEvent`
- `NutritionRiskProfile`
- `MealAnalysisResult` (API response envelope)

## API Changes
- Replace `/api/v1/meal/analyze` response with `MealAnalysisResult`.
- Update list/summary endpoints to read from validated events + nutrition/risk tables.

## Storage Changes
- Add new tables for raw observations, validated events, nutrition/risk profiles.
- Legacy `meal_records` remain but are no longer written for new flow.
- No migration/backfill.

## Testing
- Unit tests: reconciliation policy, arbitration fallback, nutrition/risk derivation.
- Persistence tests: new tables and adapters.
- API tests: new response schema and read paths.

## Risks
- Breaking clients relying on existing meal analysis response schema.
- Loss of legacy data visibility (intentional drop-legacy policy).
*** End Patch}"}---
