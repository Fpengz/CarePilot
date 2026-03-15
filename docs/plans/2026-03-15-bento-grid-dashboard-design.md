# Proportional Utility Bento-Grid Dashboard Design

**Date:** 2026-03-15
**Status:** Approved
**Target:** `apps/web/components/dashboard/`

## 1. Objective
Refine the dashboard into a cohesive 12-column bento-grid system that prioritizes "Proportional Utility," medical-grade precision, and high-density data visualization.

## 2. Context
The current dashboard uses a flexible masonry layout with 24px/32px corner radiuses. This redesign transitions to a structured 12-column grid with a 12px corner radius, left-aligned typography, and a subtle grounding grid background for a more professional, "medical-grade" look.

## 3. Design Specifications

### 3.1. 12-Column Bento-Grid Structure
*   **Metric Strip (Row 1 - 12 Cols):** A single, slim horizontal strip merging Health Signal, Adherence, Glycemic Risk, and Nutrition Goal.
    *   **Iconography:** Lucide-React (`Activity`, `CheckCircle`, `Zap`, `Target`).
    *   **Sparklines:** Smaller, elegant AreaCharts (16px height) without axes.
    *   **Alignment:** All text and values strictly left-aligned.
*   **Primary Data Zone (Row 2):**
    *   **Metabolic Correlation (8 Cols):** Expanded dual-axis chart.
    *   **Insights Action Card (4 Cols):** High-contrast "sticky note" style using a vibrant Amber glassmorphism variant.
*   **Secondary Data Zone (Row 3):**
    *   **Nutrition Balance (6 Cols):** Standardized Y-axis and font sizes.
    *   **Meal Rhythms (6 Cols):** Side-by-side with Nutrition Balance for visual harmony.

### 3.2. Visual Specs & Typography
*   **Precision Styling:** Card corner radiuses reduced to **12px**.
*   **Grounding Grid:** Subtle 10% opacity grid-line background across the dashboard container.
*   **Glassmorphism:** Enhanced 20px blur for tooltips and the Action Card.
*   **Typography:** Strict left-alignment for all headers, metrics, and labels. Standardized 9px bold uppercase for all chart axis labels.

### 3.3. Refined Colors & Icons
*   **Primary Data:** Deep Teal (#047857) and Amber (#f59e0b).
*   **Neutral Data:** Slate Gray (#475569) for placeholders and axes.
*   **Grid Lines:** `--chart-grid` at 0.1 opacity for the background grounding.

## 4. Implementation Phasing
1.  **Phase 1:** Update global styles (12px radius, grid-line background).
2.  **Phase 2:** Refactor the top metric row into a single 12-column strip.
3.  **Phase 3:** Reorganize the center and bottom rows using the new 12-column grid proportions.
4.  **Phase 4:** Standardize Y-axes, font sizes, and left-alignment across all charts.
5.  **Phase 5:** Implement the vibrant Amber "Action Card" for insights.
