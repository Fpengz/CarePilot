# High-Density Minimalist Dashboard Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the dashboard with a 3-column masonry grid, glassmorphism aesthetics, and advanced Recharts visualizations (dual-axis correlation and circular meal clock).

**Architecture:** Use a flexible CSS grid for the masonry layout. Leverage Recharts for all visualizations. Centralize typography and glassmorphism styles in Tailwind.

**Tech Stack:** React (Next.js), Recharts, Tailwind CSS, Lucide React.

---

## Chunk 1: Layout and Styling

### Task 1: Define Glassmorphism and Typography in Tailwind

**Files:**
- Modify: `apps/web/tailwind.config.ts` (if available) or `apps/web/app/globals.css`

- [ ] **Step 1: Add glassmorphism utility classes and typography variants**

```css
@layer components {
  .glass-card {
    @apply bg-white/40 dark:bg-black/40 backdrop-blur-xl border border-white/20 dark:border-white/10 shadow-xl rounded-3xl p-6 transition-all;
  }
  .status-chip {
    @apply px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider;
  }
}
```

- [ ] **Step 2: Commit styling changes**

```bash
git add apps/web/app/globals.css
git commit -m "style: add glassmorphism and status chip utility classes"
```

### Task 2: Implement 3-Column Masonry Layout in Workspace

**Files:**
- Modify: `apps/web/components/dashboard/dashboard-iteration-workspace.tsx`

- [ ] **Step 1: Update the layout structure to use a 3-column grid**

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 auto-rows-min">
  {/* Components will go here with col-span-X as needed */}
</div>
```

- [ ] **Step 2: Commit layout change**

```bash
git add apps/web/components/dashboard/dashboard-iteration-workspace.tsx
git commit -m "refactor(dashboard): implement 3-column masonry grid layout"
```

## Chunk 2: Status and Insights

### Task 3: Create HealthSignal Card

**Files:**
- Create: `apps/web/components/dashboard/health-signal.tsx`
- Modify: `apps/web/components/dashboard/dashboard-iteration-workspace.tsx`

- [ ] **Step 1: Implement the compact HealthSignal component**

```tsx
import { cn } from "@/lib/utils";

export function HealthSignal({ metabolic, risk }: { metabolic: string; risk: string }) {
  return (
    <div className="glass-card flex flex-col justify-between h-full">
      <div className="text-xs font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Health Signal</div>
      <div className="mt-4 flex flex-wrap gap-2">
        <span className="status-chip bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">Metabolic: {metabolic}</span>
        <span className="status-chip bg-slate-500/10 text-slate-600 dark:text-slate-400">Risk: {risk}</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Replace ClinicalSummary with HealthSignal in workspace**

### Task 4: Create Insights Sidebar

**Files:**
- Create: `apps/web/components/dashboard/insights-sidebar.tsx`

- [ ] **Step 1: Implement the floating Insights Sidebar**

```tsx
import { AlertCircle } from "lucide-react";

export function InsightsSidebar({ recommendation }: { recommendation: string }) {
  return (
    <div className="glass-card border-amber-500/20 bg-amber-500/5">
      <div className="flex items-center gap-2 text-amber-500 mb-4">
        <AlertCircle className="h-4 w-4" />
        <span className="text-[10px] font-bold uppercase tracking-widest">Insights</span>
      </div>
      <p className="text-sm font-medium leading-relaxed italic text-[color:var(--foreground)]">
        &quot;{recommendation}&quot;
      </p>
    </div>
  );
}
```

## Chunk 3: Advanced Visualizations

### Task 5: Implement SummaryRow with Micro-Sparklines

**Files:**
- Create: `apps/web/components/dashboard/summary-metric-card.tsx`
- Modify: `apps/web/components/dashboard/dashboard-iteration-workspace.tsx`

- [ ] **Step 1: Implement SummaryMetricCard with sparkline**

```tsx
import { Area, AreaChart, ResponsiveContainer } from "recharts";

export function SummaryMetricCard({ label, value, unit, data }: { label: string; value: number; unit: string; data: any[] }) {
  return (
    <div className="glass-card">
      <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[color:var(--muted-foreground)] mb-1">{label}</div>
      <div className="flex items-baseline gap-1">
        <span className="text-3xl font-bold tracking-tight">{value}</span>
        <span className="text-sm font-medium text-[color:var(--muted-foreground)]">{unit}</span>
      </div>
      <div className="h-8 mt-4 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <Area type="monotone" dataKey="value" stroke="var(--primary)" fill="var(--primary)" fillOpacity={0.1} strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

### Task 6: Implement CorrelationChart (Dual-Axis)

**Files:**
- Create: `apps/web/components/dashboard/correlation-chart.tsx`

- [ ] **Step 1: Implement the dual-axis ComposedChart**

```tsx
import { ComposedChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export function CorrelationChart({ calories, risk }: { calories: any[]; risk: any[] }) {
  // Merge data based on labels
  const data = calories.map((c, i) => ({
    label: c.label,
    calories: c.value,
    risk: risk[i]?.value
  }));

  return (
    <div className="glass-card col-span-2">
      <div className="text-xs font-bold uppercase tracking-widest mb-6">Metabolic Correlation</div>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data}>
            <CartesianGrid vertical={false} strokeOpacity={0.1} />
            <XAxis dataKey="label" fontSize={9} tickLine={false} axisLine={false} />
            <YAxis yAxisId="left" fontSize={9} tickLine={false} axisLine={false} />
            <YAxis yAxisId="right" orientation="right" fontSize={9} tickLine={false} axisLine={false} />
            <Tooltip />
            <Line yAxisId="left" type="monotone" dataKey="calories" stroke="#c2410c" strokeWidth={3} dot={false} />
            <Line yAxisId="right" type="monotone" dataKey="risk" stroke="#dc2626" strokeWidth={3} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

### Task 7: Implement MealClock (Circular Heat Map)

**Files:**
- Create: `apps/web/components/dashboard/meal-clock.tsx`

- [ ] **Step 1: Implement a radial heat map using RadarChart or similar**

```tsx
import { PolarGrid, PolarAngleAxis, Radar, RadarChart, ResponsiveContainer } from "recharts";

export function MealClock({ bins }: { bins: { hour: number; count: number }[] }) {
  return (
    <div className="glass-card">
      <div className="text-xs font-bold uppercase tracking-widest mb-4">Meal Rhythms (24h)</div>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="80%" data={bins}>
            <PolarGrid strokeOpacity={0.1} />
            <PolarAngleAxis dataKey="hour" fontSize={9} />
            <Radar name="Meals" dataKey="count" stroke="#047857" fill="#047857" fillOpacity={0.5} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

## Chunk 4: Integration and Cleanup

### Task 8: Final Dashboard Assembly

**Files:**
- Modify: `apps/web/components/dashboard/dashboard-iteration-workspace.tsx`

- [ ] **Step 1: Assemble all new components in the workspace masonry grid**
- [ ] **Step 2: Remove old components (ClinicalSummary, SummaryStrip, TrendPanel)**
- [ ] **Step 3: Implement zero-label placeholder logic in chart-utils.tsx**
- [ ] **Step 4: Final commit**
