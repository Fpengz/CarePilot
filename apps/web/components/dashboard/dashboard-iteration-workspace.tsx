"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

import { ErrorCard } from "@/components/app/error-card";
import { useSession } from "@/components/app/session-provider";
import { HealthSignal } from "@/components/dashboard/health-signal";
import { InsightsSidebar } from "@/components/dashboard/insights-sidebar";
import { SummaryMetricCard } from "@/components/dashboard/summary-metric-card";
import { CorrelationChart } from "@/components/dashboard/correlation-chart";
import { MealClock } from "@/components/dashboard/meal-clock";
import { RangeSelector, type RangeKey } from "@/components/dashboard/range-selector";
import { NutritionBalanceChart } from "@/components/dashboard/nutrition-balance-chart";
import { getDashboardOverview } from "@/lib/api/dashboard-client";
import type {
  DashboardOverviewApiResponse,
} from "@/lib/types";

function getDefaultCustomRange() {
  const to = new Date();
  const from = new Date(to);
  from.setDate(to.getDate() - 29);
  return {
    from: from.toISOString().slice(0, 10),
    to: to.toISOString().slice(0, 10),
  };
}

function DashboardSkeleton() {
  return (
    <div className="section-stack">
      <div className="h-64 animate-pulse rounded-2xl bg-black/[0.05]" />
      <div className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-64 animate-pulse rounded-3xl bg-black/[0.05]" />
        ))}
      </div>
    </div>
  );
}

export function DashboardIterationWorkspace() {
  const { status } = useSession();
  const [range, setRange] = useState<RangeKey>("30d");
  const [customRange, setCustomRange] = useState(getDefaultCustomRange);
  const [overview, setOverview] = useState<DashboardOverviewApiResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const deferredRange = useDeferredValue(range);
  const deferredCustomRange = useDeferredValue(customRange);

  useEffect(() => {
    if (status !== "authenticated") return;
    if (deferredRange === "custom" && (!deferredCustomRange.from || !deferredCustomRange.to)) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const response = await getDashboardOverview({
          range: deferredRange,
          from: deferredRange === "custom" ? deferredCustomRange.from : undefined,
          to: deferredRange === "custom" ? deferredCustomRange.to : undefined,
        });
        if (!cancelled) setOverview(response);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [deferredCustomRange, deferredRange, status]);

  const summarySparklines = useMemo(() => {
    if (!overview) return null;
    return {
      adherence: overview.charts.calories.points.map(p => ({ value: p.value })), // Placeholder
      risk: overview.charts.glycemic_risk.points.map(p => ({ value: p.value })),
      nutrition: overview.charts.calories.points.map(p => ({ value: p.value })), // Placeholder
    };
  }, [overview]);

  return (
    <div className="section-stack">
      {status === "unauthenticated" ? <ErrorCard message="Sign in to explore your health dashboard." /> : null}
      {error ? <ErrorCard message={error} /> : null}

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">Overview</h1>
          <p className="text-sm text-[color:var(--muted-foreground)]">
            Health signals and nutrition insights for the selected period.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <RangeSelector
            range={range}
            onRangeChange={setRange}
            customRange={customRange}
            onCustomRangeChange={setCustomRange}
          />
        </div>
      </div>

      {loading && !overview ? <DashboardSkeleton /> : null}

      {overview && summarySparklines ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 auto-rows-min">
          {/* Row 1 */}
          <HealthSignal 
            metabolic={overview.summary.adherence_score.value > 80 ? "Balanced" : "Variable"} 
            risk={overview.summary.glycemic_risk.value < 30 ? "Low" : "High"} 
          />
          <SummaryMetricCard 
            label="Adherence" 
            value={Math.round(overview.summary.adherence_score.value)} 
            unit="%" 
            data={summarySparklines.adherence} 
          />
          <SummaryMetricCard 
            label="Glycemic Risk" 
            value={Math.round(overview.summary.glycemic_risk.value)} 
            unit="/100" 
            data={summarySparklines.risk} 
          />

          {/* Row 2 */}
          <SummaryMetricCard 
            label="Nutrition Goal" 
            value={Math.round(overview.summary.nutrition_goal_score.value)} 
            unit="%" 
            data={summarySparklines.nutrition} 
          />
          <CorrelationChart 
            calories={overview.charts.calories.points} 
            risk={overview.charts.glycemic_risk.points} 
          />

          {/* Row 3 */}
          <NutritionBalanceChart chart={overview.charts.macros} />
          <MealClock bins={overview.charts.meal_timing.bins} />
          <InsightsSidebar 
            recommendation={overview.insights.recommendations[0] ?? "Keep tracking your meals to reveal deeper insights."} 
          />
        </div>
      ) : null}
    </div>
  );
}
