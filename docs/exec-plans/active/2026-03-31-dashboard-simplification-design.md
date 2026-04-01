# Design Doc: Dashboard Simplification (Surgical Cleanup)

- **Date:** 2026-03-31
- **Status:** Approved
- **Topic:** Dashboard cleanup and simplification

## Context
The dashboard page (`apps/web/app/dashboard/page.tsx`) contains imports for components that are not currently used in the layout. Additionally, several components in `apps/web/components/dashboard/` are redundant with `ClinicalSummary` or appear to be remnants of earlier design iterations.

## Goal
Improve codebase maintainability and reduce bundle size by removing unused and redundant dashboard components.

## Proposed Changes

### 1. Page Cleanup
- Remove the unused `MetricStrip` import from `apps/web/app/dashboard/page.tsx`.

### 2. Component Deletion
The following files in `apps/web/components/dashboard/` will be deleted as they are unreferenced and redundant:
- `metric-strip.tsx` (Redundant with `ClinicalSummary`)
- `summary-strip.tsx` (Unused)
- `health-signal.tsx` (Unused)
- `insights-sidebar.tsx` (Unused)
- `summary-metric-card.tsx` (Unused)
- `trend-panel.tsx` (Unused)

## Success Criteria
- The dashboard page renders identically to its current state.
- `pnpm web:build` passes successfully.
- No references to the deleted components remain in the codebase.

## Risk Assessment
- **Low Risk:** These components are confirmed to be unreferenced via `grep`. The primary risk is a missing reference in a file not covered by the search, but standard project structure suggests this is unlikely.
