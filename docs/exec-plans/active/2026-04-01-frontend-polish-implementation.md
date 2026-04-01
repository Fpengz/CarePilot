# Frontend UX: Final Un-Slop Polish Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute final polish on the frontend to improve hierarchy, rhythm, and data storytelling.

**Architecture:** 
1.  Update `apps/web/app/globals.css` to refine typography and contrast.
2.  Refactor Dashboard and Chat components to improve spacing and reduce "grid fatigue."
3.  Add "story headlines" to major charts in `apps/web/components/dashboard/`.

**Tech Stack:** React, TailwindCSS, Lucide React.

---

## Chunk 1: Typography & Contrast

### Task 1: Refine Typography

**Files:**
- Modify: `apps/web/app/globals.css`

- [ ] **Step 1: Update H1/H2 contrast and weight**

- [ ] **Step 2: Restrict uppercase micro-labels to section headers only**

- [ ] **Step 3: Commit**

---

## Chunk 2: Visual Rhythm

### Task 2: Improve Spacing and Layout

**Files:**
- Modify: `apps/web/app/dashboard/page.tsx`
- Modify: `apps/web/app/chat/page.tsx`

- [ ] **Step 1: Introduce non-card sections for key metrics to break "card wall"**

- [ ] **Step 2: Vary vertical spacing between components**

- [ ] **Step 3: Commit**

---

## Chunk 3: Data Storytelling

### Task 3: Add Story Headlines to Charts

**Files:**
- Modify: `apps/web/components/dashboard/blood-pressure-chart.tsx`
- Modify: `apps/web/components/dashboard/nutrition-balance-chart.tsx`

- [ ] **Step 1: Add a one-line "story headline" (e.g., "Your blood pressure is stabilizing") above the BP chart**

- [ ] **Step 2: Add a similar headline above the nutrition chart**

- [ ] **Step 3: Commit**

---

## Chunk 4: Final Verification

### Task 4: UI/UX Gate

- [ ] **Step 1: Run `pnpm web:build` to ensure no build errors**

- [ ] **Step 2: Visual verification (simulated or via Playwright if available)**

- [ ] **Step 3: Commit and Open PR**
