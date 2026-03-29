# Nutrition Balance Chart Design (Recharts Migration)

**Date:** 2026-03-15
**Status:** Approved
**Target:** `apps/web/components/dashboard/`

## 1. Objective
Implement a highly interactive "Nutrition Balance" chart using **Recharts** to provide deep insights into daily macro-nutrient consumption. This initiative also includes a full refactor of existing custom dashboard charts (`MetricLineChart`, `MealTimingHistogram`) to a unified, library-backed architecture for better maintainability and UX.

## 2. Context
The current dashboard uses custom-built SVG and CSS components for charting. While functional, these components are difficult to extend with complex features like multi-series toggling, advanced tooltips, and responsive axes. Moving to Recharts will standardize the visualization layer.

## 3. Design Specifications

### 3.1. The New `NutritionBalanceChart`
*   **Purpose:** Visualize daily protein, carbohydrate, and fat intake.
*   **Data Source:** `DashboardMacroChartApi` from `/api/v1/dashboard`.
*   **Modes:**
    *   **All:** Stacked bar chart showing total macro composition.
    *   **Protein only:** Single bar chart showing protein (Amber-500: `#f59e0b`).
    *   **Carbohydrates only:** Single bar chart showing carbs (Green-700: `#047857`).
    *   **Fat only:** Single bar chart showing fat (Violet-600: `#9333ea`).
*   **Controls:** A segmented control (Tabs) above the chart for switching modes.
*   **Interactivity:**
    *   Custom `<ClinicalTooltip>` showing exact values (g) and total calories (kcal).
    *   Hover effects with subtle scaling and opacity changes.
    *   Smooth entry and transition animations (400ms duration).

### 3.2. Dashboard Refactoring Strategy
All charts will be migrated to Recharts to ensure visual and codebase parity:
*   **`MetricLineChart`:** Converted to Recharts `<LineChart>` with `type="monotone"`. Glycemic risk threshold bands will use `<ReferenceArea>`.
*   **`MealTimingHistogram`:** Converted to Recharts `<BarChart>` with custom coloring for peak hours.
*   **Shared Utilities:** Extract common axis, grid, and tooltip styles into a `chart-utils.tsx` file.

### 3.3. Visual Consistency ("Clinical Calm")
*   **Typography:** 9px bold uppercase for axis labels, 12px for tooltips.
*   **Grid:** Light strokes using `--chart-grid` color with 0.4 opacity.
*   **Theme:** Fully dark/light mode responsive via CSS variables (`--foreground`, `--muted-foreground`).

## 4. Implementation Phasing
1.  **Phase 1:** Install `recharts` and establish shared chart utilities.
2.  **Phase 2:** Implement `NutritionBalanceChart` and integrate into the dashboard.
3.  **Phase 3:** Incrementally refactor `MetricLineChart` and `MealTimingHistogram`.
4.  **Phase 4:** Final visual polish and responsive testing.
