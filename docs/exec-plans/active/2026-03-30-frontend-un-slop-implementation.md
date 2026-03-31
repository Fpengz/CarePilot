# Frontend "Un-Slop" Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the CarePilot web interface from a templated feel into a professional, medical-grade experience by establishing new tokens and reworking the Dashboard as a North Star.

**Architecture:** Update global CSS variables, refactor Tailwind config, and systematically overhaul core page components to reduce container nesting and improve hierarchy.

**Tech Stack:** Next.js 14 (App Router), Tailwind CSS, Lucide React, Recharts.

---

## Chunk 1: Design System Foundation

### Task 1: Update Global Design Tokens
**Files:**
- Modify: `apps/web/app/globals.css`
- Modify: `apps/web/tailwind.config.js`

- [ ] **Step 1: Define new CSS variables in globals.css**
  Add `--surface`, `--panel`, `--raised`, `--accent-teal`, `--accent-teal-muted`.
- [ ] **Step 2: Update Tailwind config to map these variables**
  Ensure `extend.colors` includes the new semantic tokens.
- [ ] **Step 3: Update Typography scale in tailwind.config.js**
  Define `display` and `body` font families and custom font sizes for H1-H4.
- [ ] **Step 4: Verify local dev build**
  Run `pnpm dev` and ensure no breaking CSS errors.
- [ ] **Step 5: Commit**
  `git add apps/web/app/globals.css apps/web/tailwind.config.js && git commit -m "style: establish new design tokens for un-slop pass"`

---

## Chunk 2: Dashboard Header & Metric Strip

### Task 2: Refactor Dashboard Header
**Files:**
- Modify: `apps/web/app/dashboard/page.tsx`

- [ ] **Step 1: Increase H1 size and weight**
  Use `text-4xl font-semibold tracking-tight`.
- [ ] **Step 2: Mute or remove uppercase micro-labels**
  Change "Patient Trends, Insights & Analytics" to a standard font weight and mixed case if appropriate.
- [ ] **Step 3: Commit**
  `git commit -am "style: overhaul dashboard header hierarchy"`

### Task 3: Overhaul Metric Strip Component
**Files:**
- Modify: `apps/web/components/dashboard/metric-strip.tsx`

- [ ] **Step 1: Consolidate glass cards into a single bar**
  Remove `glass-card` class from individual items; use a single `--panel` background for the strip.
- [ ] **Step 2: Add vertical dividers between metrics**
  Use subtle border-r or dividers.
- [ ] **Step 3: Update sparkline styles**
  Increase contrast and add hover tooltips.
- [ ] **Step 4: Commit**
  `git commit -am "style: refactor metric strip into a cohesive unit"`

---

## Chunk 3: Dashboard Layout & Section Grouping

### Task 4: Hero Clinical Summary
**Files:**
- Modify: `apps/web/components/dashboard/clinical-summary.tsx`
- Modify: `apps/web/app/dashboard/page.tsx`

- [ ] **Step 1: Remove card borders from ClinicalSummary**
  Use whitespace and background contrast to define the hero area.
- [ ] **Step 2: Increase primary metric prominence**
  Make the main scores (84, etc.) larger and more central.
- [ ] **Step 3: Update status chips**
  Use new high-contrast teal/amber tokens.
- [ ] **Step 4: Commit**
  `git commit -am "style: elevate clinical summary to hero section"`

### Task 5: Daily Rhythms Grouping
**Files:**
- Modify: `apps/web/app/dashboard/page.tsx`

- [ ] **Step 1: Group charts under a story headline**
  Add a `<h2>` with a descriptive headline like "Daily Rhythms & Balance".
- [ ] **Step 2: Remove individual card backgrounds if possible**
  Try placing charts directly on a shared `--panel` background.
- [ ] **Step 3: Commit**
  `git commit -am "style: group dashboard charts under story headlines"`

---

## Chunk 4: Final Validation & Triage

### Task 6: Responsive & Touch Target Audit
**Files:**
- Modify: `apps/web/components/ui/button.tsx` (if needed)
- Modify: `apps/web/app/dashboard/page.tsx`

- [ ] **Step 1: Ensure all buttons are at least 44px height**
- [ ] **Step 2: Verify 1-column layout on mobile (< 640px)**
- [ ] **Step 3: Run comprehensive gate**
  `uv run python scripts/cli.py test web`
- [ ] **Step 4: Commit**
  `git commit -m "style: final polish and responsive fixes for dashboard overhaul"`
