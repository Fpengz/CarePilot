# Proportional Utility Bento-Grid Dashboard Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refine the dashboard into a cohesive 12-column bento-grid system with a 12px corner radius, left-aligned typography, and a grounded grid background.

**Architecture:** Use a 12-column grid layout with Row-based zones. Standardize card styling and alignment across all dashboard components.

**Tech Stack:** React (Next.js), Recharts, Tailwind CSS, Lucide React.

---

## Chunk 1: Global Visual Refinement

### Task 1: Update Global Styles for Precision Aesthetic

**Files:**
- Modify: `apps/web/app/globals.css`

- [ ] **Step 1: Reduce card corner radius to 12px and add grounding grid background**

```css
@layer components {
  .glass-card {
    @apply bg-white/40 dark:bg-black/40 backdrop-blur-xl border border-white/20 dark:border-white/10 shadow-xl rounded-xl p-6 transition-all; /* Changed rounded-3xl to rounded-xl (12px) */
  }
  
  .dashboard-grounding {
    background-image: 
      linear-gradient(to right, var(--chart-grid) 1px, transparent 1px),
      linear-gradient(to bottom, var(--chart-grid) 1px, transparent 1px);
    background-size: 40px 40px;
    background-position: center;
    @apply opacity-[0.05]; /* 5% to 10% opacity */
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: -1;
  }
}
```

- [ ] **Step 2: Commit global style updates**

```bash
git add apps/web/app/globals.css
git commit -m "style: reduce card radius to 12px and add grounding grid background"
```

## Chunk 2: Layout Reorganization

### Task 2: Refactor Metric Strip into Single 12-Column Row

**Files:**
- Create: `apps/web/components/dashboard/metric-strip.tsx`
- Modify: `apps/web/components/dashboard/dashboard-iteration-workspace.tsx`

- [ ] **Step 1: Implement the slim MetricStrip component with Lucide icons**

```tsx
import { Activity, CheckCircle, Zap, Target } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";

interface MetricItemProps {
  label: string;
  value: string;
  unit?: string;
  data: any[];
  icon: React.ReactNode;
}

function MetricItem({ label, value, unit, data, icon }: MetricItemProps) {
  return (
    <div className="flex flex-1 flex-col items-start gap-1 px-4 first:pl-0 last:pr-0 border-r border-white/10 last:border-0">
      <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">
        {icon}
        <span>{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-xl font-bold tracking-tight">{value}</span>
        {unit && <span className="text-xs font-medium text-[color:var(--muted-foreground)]">{unit}</span>}
      </div>
      <div className="h-4 mt-1 w-full opacity-50">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <Area type="monotone" dataKey="value" stroke="var(--primary)" fill="var(--primary)" fillOpacity={0.1} strokeWidth={1.5} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function MetricStrip({ overview, sparklines }: { overview: any; sparklines: any }) {
  return (
    <div className="glass-card col-span-12 !py-4 flex items-center divide-x divide-white/5 overflow-x-auto scrollbar-hide">
      <MetricItem 
        label="Signal" 
        value={overview.summary.adherence_score.value > 80 ? "Stable" : "Variable"} 
        icon={<Activity className="h-3 w-3" />}
        data={sparklines.adherence}
      />
      <MetricItem 
        label="Adherence" 
        value={Math.round(overview.summary.adherence_score.value).toString()} 
        unit="%" 
        icon={<CheckCircle className="h-3 w-3" />}
        data={sparklines.adherence}
      />
      <MetricItem 
        label="Risk" 
        value={Math.round(overview.summary.glycemic_risk.value).toString()} 
        unit="/100" 
        icon={<Zap className="h-3 w-3" />}
        data={sparklines.risk}
      />
      <MetricItem 
        label="Goal" 
        value={Math.round(overview.summary.nutrition_goal_score.value).toString()} 
        unit="%" 
        icon={<Target className="h-3 w-3" />}
        data={sparklines.nutrition}
      />
    </div>
  );
}
```

- [ ] **Step 2: Update workspace layout to use the 12-column grid and MetricStrip**

```tsx
<div className="relative isolate">
  <div className="dashboard-grounding" />
  <div className="grid grid-cols-12 gap-6">
    <MetricStrip overview={overview} sparklines={summarySparklines} />
    {/* Middle Row */}
    <div className="col-span-12 lg:col-span-8">
      <CorrelationChart calories={overview.charts.calories.points} risk={overview.charts.glycemic_risk.points} />
    </div>
    <div className="col-span-12 lg:col-span-4">
      <InsightsSidebar recommendation={overview.insights.recommendations[0]} />
    </div>
    {/* Bottom Row */}
    <div className="col-span-12 lg:col-span-6">
      <NutritionBalanceChart chart={overview.charts.macros} />
    </div>
    <div className="col-span-12 lg:col-span-6">
      <MealClock bins={overview.charts.meal_timing.bins} />
    </div>
  </div>
</div>
```

## Chunk 3: Component Refinement

### Task 3: Refine Action Card (Insights) and Tooltips

**Files:**
- Modify: `apps/web/components/dashboard/insights-sidebar.tsx`
- Modify: `apps/web/components/dashboard/chart-utils.tsx`

- [ ] **Step 1: Style InsightsSidebar as a vibrant Amber Action Card**

```tsx
export function InsightsSidebar({ recommendation }: { recommendation: string }) {
  return (
    <div className="glass-card h-full border-amber-500/30 bg-amber-500/10 shadow-[0_8px_32px_rgba(245,158,11,0.15)] flex flex-col justify-center">
      <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400 mb-3">
        <AlertCircle className="h-4 w-4" />
        <span className="text-[10px] font-bold uppercase tracking-[0.2em]">Action Insight</span>
      </div>
      <p className="text-sm font-semibold leading-relaxed text-[color:var(--foreground)] pr-4 border-l-2 border-amber-500/50 pl-4 py-1">
        {recommendation}
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Increase Tooltip blur to 20px in chart-utils.tsx**

```tsx
export const ClinicalTooltip = ({ active, payload, label }: TooltipProps<ValueType, NameType>) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-xl border border-white/20 bg-white/40 dark:bg-black/40 p-3 shadow-2xl backdrop-blur-[20px]">
        {/* ... */}
      </div>
    );
  }
  return null;
};
```

### Task 4: Standardize Charts for Visual Harmony

**Files:**
- Modify: `apps/web/components/dashboard/correlation-chart.tsx`
- Modify: `apps/web/components/dashboard/meal-clock.tsx`
- Modify: `apps/web/components/dashboard/nutrition-balance-chart.tsx`

- [ ] **Step 1: Enforce left-alignment and standardize Y-axis/typography in all charts**
- [ ] **Step 2: Commit final refinements**

```bash
git add apps/web/components/dashboard/
git commit -m "feat(dashboard): standardize alignment and visual harmony across all bento cards"
```
