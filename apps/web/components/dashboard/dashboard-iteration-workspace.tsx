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
import { MetricStrip } from "@/components/dashboard/metric-strip";
import { InsightsSidebar } from "@/components/dashboard/insights-sidebar";
import { CorrelationChart } from "@/components/dashboard/correlation-chart";
import { MealClock } from "@/components/dashboard/meal-clock";
import { RangeSelector, type RangeKey } from "@/components/dashboard/range-selector";
import { NutritionBalanceChart } from "@/components/dashboard/nutrition-balance-chart";
import { BloodPressureChart } from "@/components/dashboard/blood-pressure-chart";
import { getDashboardOverview } from "@/lib/api/dashboard-client";
import { listMealRecords } from "@/lib/api/meal-client";
import { formatDateKey, parseDateKey } from "@/lib/time";
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

function shiftDateKey(dateKey: string, days: number): string {
  const parsed = parseDateKey(dateKey);
  if (!parsed) return formatDateKey(new Date());
  parsed.setUTCDate(parsed.getUTCDate() + days);
  return formatDateKey(parsed);
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
  const [autoRangeApplied, setAutoRangeApplied] = useState(false);
  const [overview, setOverview] = useState<DashboardOverviewApiResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const deferredRange = useDeferredValue(range);
  const deferredCustomRange = useDeferredValue(customRange);

  useEffect(() => {
    if (status !== "authenticated" || autoRangeApplied) return;
    let cancelled = false;
    async function loadLatestRange() {
      try {
        const latest = await listMealRecords(1);
        if (cancelled) return;
        const record = latest.records?.[0];
        const raw = record?.captured_at ?? record?.created_at;
        const latestKey = raw ? formatDateKey(raw) : formatDateKey(new Date());
        setCustomRange({
          from: shiftDateKey(latestKey, -29),
          to: latestKey,
        });
        setRange("custom");
        setAutoRangeApplied(true);
      } catch (err) {
        if (!cancelled) setAutoRangeApplied(true);
      }
    }
    void loadLatestRange();
    return () => {
      cancelled = true;
    };
  }, [autoRangeApplied, status]);

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
        <div className="relative isolate">
          <div className="dashboard-grounding" />
          <div className="grid grid-cols-12 gap-6">
            <MetricStrip overview={overview} sparklines={summarySparklines} />
            
            {/* Middle Row */}
            <div className="col-span-12 flex flex-col gap-6">
              <CorrelationChart 
                calories={overview.charts.calories.points} 
                risk={overview.charts.glycemic_risk.points} 
              />
              {/*<div className="h-24">*/}
              {/*  <InsightsSidebar */}
              {/*    recommendation={overview.insights.recommendations[0] ?? "Keep tracking your meals to reveal deeper insights."} */}
              {/*  />*/}
              {/*</div>*/}
            </div>

            {/* Bottom Row */}
            <div className="col-span-12 lg:col-span-6">
              <NutritionBalanceChart chart={overview.charts.macros} />
            </div>
            <div className="col-span-12 lg:col-span-6">
              <MealClock bins={overview.charts.meal_timing.bins} />
            </div>
            <div className="col-span-12">
              <BloodPressureChart chart={overview?.charts.blood_pressure} loading={loading} />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
