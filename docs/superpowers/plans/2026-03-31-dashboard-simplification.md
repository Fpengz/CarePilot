# Dashboard Simplification Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove unused and redundant dashboard components to simplify the codebase.

**Architecture:** Surgical removal of unreferenced React components and unused imports.

**Tech Stack:** Next.js (React), TypeScript

---

### Task 1: Clean up Dashboard Page

**Files:**
- Modify: `apps/web/app/dashboard/page.tsx`

- [ ] **Step 1: Remove unused import**
Remove `import { MetricStrip } from "@/components/dashboard/metric-strip";` (Line 13)

- [ ] **Step 2: Verify page still builds**
Run: `pnpm web:build` (in `apps/web`) or just check for lint errors if faster.
Expected: Build passes.

- [ ] **Step 3: Commit**
```bash
git add apps/web/app/dashboard/page.tsx
git commit -m "refactor(web): remove unused MetricStrip import from dashboard page"
```

### Task 2: Delete Redundant Components

**Files:**
- Delete: `apps/web/components/dashboard/metric-strip.tsx`
- Delete: `apps/web/components/dashboard/summary-strip.tsx`
- Delete: `apps/web/components/dashboard/health-signal.tsx`
- Delete: `apps/web/components/dashboard/insights-sidebar.tsx`
- Delete: `apps/web/components/dashboard/summary-metric-card.tsx`
- Delete: `apps/web/components/dashboard/trend-panel.tsx`

- [ ] **Step 1: Delete the files**
Run: `rm apps/web/components/dashboard/{metric-strip.tsx,summary-strip.tsx,health-signal.tsx,insights-sidebar.tsx,summary-metric-card.tsx,trend-panel.tsx}`

- [ ] **Step 2: Verify no remaining references**
Run: `grep -rE "MetricStrip|SummaryStrip|HealthSignal|InsightsSidebar|SummaryMetricCard|TrendPanel" apps/web`
Expected: No matches in component usage (ignore the deleted files if they still show in grep cache).

- [ ] **Step 3: Run final build check**
Run: `pnpm web:build`
Expected: Build passes.

- [ ] **Step 4: Commit**
```bash
git add apps/web/components/dashboard/
git commit -m "refactor(web): delete redundant and unused dashboard components"
```
