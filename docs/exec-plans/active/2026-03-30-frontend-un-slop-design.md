# Design for Frontend "Un-Slop" and Structural Simplification

**Date:** 2026-03-30
**Status:** Approved
**Topic:** Frontend UX Hardening

## 1. Objective
Transform the CarePilot web interface from an "AI-slop" templated feel (repeated glass cards, micro-labels, hierarchy flattening) into a professional, medical-grade, and "clinical editorial" experience.

## 2. Design Foundation

### 2.1. Global Tokens (Design System)
*   **Colors**:
    *   `--surface`: #FDFDFD (Base background)
    *   `--panel`: #F8F9FA (Secondary background for grouping)
    *   `--raised`: #FFFFFF (Interactive elements with shadow)
    *   `--accent`: #0D9488 (Restrained Medical Teal)
    *   `--accent-muted`: #F0FDFA (Soft teal background)
*   **Typography**:
    *   `--font-display`: Inter Semibold (Headings, -0.02em tracking)
    *   `--font-body`: Inter Regular (Content)
    *   **Scale**: Increase H1 to 2.5rem (40px) and H2 to 1.5rem (24px). Reduce micro-labels to 0.7rem (11px).
*   **Spacing**:
    *   Standardize on an 8px base rhythm.
    *   Airy zone padding: 2rem (32px).
    *   Tight cluster spacing: 0.5rem (8px).

### 2.2. Layout Patterns
*   **Container Reduction**: Replace 50% of card borders/shadows with background tints (`--panel`) or vertical separation lines.
*   **Section Dominance**: Every page must have one visually dominant primary section.
*   **Story Headlines**: Major sections and charts must have data-driven descriptive headlines instead of generic titles.

## 3. Dashboard Overhaul (The North Star)

### 3.1. Header & Metric Strip
*   **Header**: High-contrast H1. Upper-case labels removed or moved to muted kicker text.
*   **Metric Strip**: Refactor from "card grid" into a "single cohesive bar". Interactive sparklines with hover tooltips showing +/- vs target.

### 3.2. Clinical Summary (Hero)
*   Make the "Summary" the focal point.
*   Remove borders; use whitespace and large typography to define the area.
*   Bold status chips: `Signal: Stable`, `Risk: Low`.

### 3.3. Daily Rhythms & Vitals
*   Group Nutrition Balance and Meal Clock under "Daily Rhythms" story headline.
*   Move Blood Pressure to a utilitarian "Baseline Vitals" section at the bottom.

## 4. Implementation Phasing
1.  **Phase 1**: Update `globals.css` and `tailwind.config.js` with new tokens.
2.  **Phase 2**: Refactor Dashboard Header and Metric Strip.
3.  **Phase 3**: Implement Hero Clinical Summary and Section Grouping.
4.  **Phase 4**: Apply patterns to Chat and Companion pages.

## 5. Success Criteria
*   Visual hierarchy is obvious at a glance.
*   Uppercase micro-labels reduced by >60%.
*   "Card fatigue" reduced by introducing non-bordered grouping.
*   Minimum 44x44 touch targets for all mobile actions.
