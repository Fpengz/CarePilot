# Nutrition Balance Recharts Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace custom SVG dashboard charts with a unified Recharts-based implementation, starting with a new interactive Nutrition Balance chart.

**Architecture:** Use Recharts for all visualizations. Centralize shared styles (axes, grids, tooltips) into a `chart-utils.tsx` file to maintain the "Clinical Calm" aesthetic. Incrementally refactor existing charts to use this unified approach.

**Tech Stack:** Recharts, React (Next.js), Tailwind CSS.

---

## Chunk 1: Setup and Shared Utilities

### Task 1: Install Recharts

**Files:**
- Modify: `apps/web/package.json`

- [ ] **Step 1: Add recharts to dependencies**
- [ ] **Step 2: Run install command**

Run: `pnpm install recharts` (or `npm install recharts` based on project preference)
Expected: `recharts` added to `package.json` and `node_modules`.

### Task 2: Create Shared Chart Utilities

**Files:**
- Create: `apps/web/components/dashboard/chart-utils.tsx`

- [ ] **Step 1: Implement shared chart configurations and custom components**

```tsx
import { TooltipProps } from 'recharts';
import { NameType, ValueType } from 'recharts/types/component/DefaultTooltipContent';

export const CHART_COLORS = {
  protein: "#f59e0b",
  carbs: "#047857",
  fat: "#9333ea",
  calories: "#c2410c",
  risk: "#dc2626",
};

export const COMMON_AXIS_PROPS = {
  stroke: "var(--chart-text)",
  fontSize: 9,
  fontWeight: "bold",
  tickLine: false,
  axisLine: false,
};

export const ClinicalTooltip = ({ active, payload, label }: TooltipProps<ValueType, NameType>) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-xl border border-[color:var(--chart-grid)] bg-[color:var(--chart-bg)] p-3 shadow-xl backdrop-blur-md">
        <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)]">{label}</p>
        <div className="space-y-1.5">
          {payload.map((entry) => (
            <div key={entry.name} className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <div className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: entry.color }} />
                <span className="text-xs font-medium text-[color:var(--foreground)]">{entry.name}</span>
              </div>
              <span className="text-xs font-bold tabular-nums text-[color:var(--foreground)]">
                {entry.value}{entry.unit || 'g'}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};
```

- [ ] **Step 2: Commit utilities**

```bash
git add apps/web/components/dashboard/chart-utils.tsx
git commit -m "feat(dashboard): add shared chart utilities for Recharts"
```

## Chunk 2: Nutrition Balance Chart

### Task 3: Implement NutritionBalanceChart Component

**Files:**
- Create: `apps/web/components/dashboard/nutrition-balance-chart.tsx`

- [ ] **Step 1: Build the NutritionBalanceChart with mode switching**

```tsx
"use client";

import { useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";
import { DashboardMacroChartApi } from "@/lib/types";
import { CHART_COLORS, COMMON_AXIS_PROPS, ClinicalTooltip } from "./chart-utils";
import { cn } from "@/lib/utils";

type ViewMode = "all" | "protein" | "carbs" | "fat";

export function NutritionBalanceChart({ chart }: { chart: DashboardMacroChartApi }) {
  const [view, setView] = useState<ViewMode>("all");
  const data = chart.points;

  const modes: { id: ViewMode; label: string; color: string }[] = [
    { id: "all", label: "All", color: "var(--foreground)" },
    { id: "protein", label: "Protein", color: CHART_COLORS.protein },
    { id: "carbs", label: "Carbs", color: CHART_COLORS.carbs },
    { id: "fat", label: "Fat", color: CHART_COLORS.fat },
  ];

  return (
    <section className="metric-card">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="text-sm font-semibold text-[color:var(--foreground)]">{chart.title}</div>
          <p className="mt-1 text-xs text-[color:var(--muted-foreground)]">Daily macro balance breakdown.</p>
        </div>
        <div className="flex bg-black/5 dark:bg-white/5 p-1 rounded-lg">
          {modes.map((m) => (
            <button
              key={m.id}
              onClick={() => setView(m.id)}
              className={cn(
                "px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all",
                view === m.id ? "bg-white dark:bg-black shadow-sm text-[color:var(--foreground)]" : "text-[color:var(--muted-foreground)] hover:text-[color:var(--foreground)]"
              )}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6 h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--chart-grid)" strokeOpacity={0.4} />
            <XAxis dataKey="label" {...COMMON_AXIS_PROPS} tickMargin={10} />
            <YAxis {...COMMON_AXIS_PROPS} tickMargin={10} />
            <Tooltip content={<ClinicalTooltip />} cursor={{ fill: "var(--chart-grid)", fillOpacity: 0.1 }} />
            
            {(view === "all" || view === "protein") && (
              <Bar dataKey="protein_g" name="Protein" fill={CHART_COLORS.protein} stackId="a" radius={view === "protein" ? [4, 4, 0, 0] : [0, 0, 0, 0]} />
            )}
            {(view === "all" || view === "carbs") && (
              <Bar dataKey="carbs_g" name="Carbs" fill={CHART_COLORS.carbs} stackId="a" radius={view === "carbs" ? [4, 4, 0, 0] : [0, 0, 0, 0]} />
            )}
            {(view === "all" || view === "fat") && (
              <Bar dataKey="fat_g" name="Fat" fill={CHART_COLORS.fat} stackId="a" radius={[4, 4, 0, 0]} />
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Commit new component**

```bash
git add apps/web/components/dashboard/nutrition-balance-chart.tsx
git commit -m "feat(dashboard): implement interactive NutritionBalanceChart with Recharts"
```

## Chunk 3: Dashboard Integration and Refactoring

### Task 4: Integrate New Chart into Workspace

**Files:**
- Modify: `apps/web/components/dashboard/dashboard-iteration-workspace.tsx`

- [ ] **Step 1: Import and use NutritionBalanceChart, removing the old MacroStackChart**
- [ ] **Step 2: (Optional but recommended) Refactor MetricLineChart to use Recharts LineChart**
- [ ] **Step 3: (Optional but recommended) Refactor MealTimingHistogram to use Recharts BarChart**

- [ ] **Step 4: Commit integration**

```bash
git add apps/web/components/dashboard/dashboard-iteration-workspace.tsx
git commit -m "refactor(dashboard): unify charts using Recharts and integrate new NutritionBalanceChart"
```

## Chunk 4: Final Polish

### Task 5: Verify Responsive Design and Visual Parity

- [ ] **Step 1: Test different date ranges**
- [ ] **Step 2: Verify dark/light mode consistency**
- [ ] **Step 3: Final commit for polish**
