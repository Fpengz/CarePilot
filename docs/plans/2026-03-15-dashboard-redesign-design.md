# Dietary Guardian Dashboard Redesign (High-Density & Minimalist)

**Date:** 2026-03-15
**Status:** Approved
**Target:** `apps/web/components/dashboard/`

## 1. Objective
Redesign the "Dietary Guardian" health dashboard to achieve a high-density, minimalist aesthetic that prioritizes high-level health signals and clear, actionable insights over verbose textual summaries.

## 2. Context
The current dashboard uses a traditional, text-heavy banner (`ClinicalSummary`) and standard vertical stacking. The redesign will transition to a 3-column masonry layout with advanced data visualizations and a standardized typography/visual system ("Clinical Calm").

## 3. Design Specifications

### 3.1. Layout & Hierarchy (Masonry Grid)
*   **3-Column Flexible Grid:** Supports 1x1, 2x1, and full-width spanning.
*   **Summary Row (Full Width):** Three compact cards (Adherence, Glycemic Risk, Nutrition) featuring:
    *   Large, bold numerals (32px semi-bold).
    *   Micro-sparklines (Recharts `AreaChart` without axes).
*   **Health Signal Card (1x1, Top-Left):** Replaces the `ClinicalSummary` header.
    *   Compact, glassmorphism card.
    *   Concise status chips: `Metabolic: Balanced` (Teal), `Risk: Low` (Slate).
*   **Insights Sidebar (Fixed, Right Column):** A vertical, floating-effect sidebar for "Action Required" items.
*   **Correlation Chart (2x1 Span):** Dual-axis Recharts `ComposedChart` combining Daily Calories (Left Y-Axis) and Glycemic Risk (Right Y-Axis).
*   **Nutrition Balance (1x1):** The recently added stacked bar chart, refined with new card styles.
*   **Meal Clock (1x1):** A 24-hour circular radial heat map for visualizing meal timing density.

### 3.2. Visual Style & Typography
*   **Glassmorphism:** `backdrop-filter: blur(16px)`, semi-transparent borders, and 24px inner padding.
*   **Typography:** Geometric sans-serif (Inter) with distinct weight variations.
    *   **Status Chips:** 10px bold uppercase.
    *   **Metrics:** 32px semi-bold.
    *   **Labels:** 11px medium.
*   **Refined Color Palette:**
    *   **Deep Teal (#047857):** Stability and primary data.
    *   **Amber (#f59e0b):** Warnings and warnings.
    *   **Slate Gray (#475569):** Neutral data and empty states.

### 3.3. Chart Refinements
*   **Zero-Label Removal:** Replace "0" labels on empty dates with subtle baseline placeholders.
*   **Dual-Axis Tooltips:** Combined tooltip showing both calories and risk score correlations.
*   **Meal Timing (Clock Face):** A Recharts `RadarChart` or a custom radial SVG implementation representing the 24-hour cycle.

## 4. Implementation Phasing
1.  **Phase 1:** Implement the 3-column masonry layout and the "Health Signal" card.
2.  **Phase 2:** Create the "Summary Row" with large metrics and micro-sparklines.
3.  **Phase 3:** Develop the dual-axis correlation chart and the circular meal clock.
4.  **Phase 4:** Build the floating "Insights" sidebar and refine the overall visual style (Glassmorphism, Typography).
5.  **Phase 5:** Final visual polish and responsive testing.
