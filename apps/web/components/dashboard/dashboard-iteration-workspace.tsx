"use client";

import dynamic from "next/dynamic";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { ErrorCard } from "@/components/app/error-card";
import { useSession } from "@/components/app/session-provider";
import { MetricStrip } from "@/components/dashboard/metric-strip";
import { RangeSelector, type RangeKey } from "@/components/dashboard/range-selector";
import { getDashboardOverview } from "@/lib/api/dashboard-client";
import { listMealRecords } from "@/lib/api/meal-client";
import { formatDateKey, parseDateKey } from "@/lib/time";

// Dynamic imports for heavy chart components (bundle-dynamic-imports)
const CorrelationChart = dynamic(() => import("@/components/dashboard/correlation-chart").then(m => m.CorrelationChart), {
  loading: () => <div className="h-64 animate-pulse rounded-3xl bg-black/[0.05]" />
});
const MealClock = dynamic(() => import("@/components/dashboard/meal-clock").then(m => m.MealClock), {
  loading: () => <div className="h-64 animate-pulse rounded-3xl bg-black/[0.05]" />
});
const NutritionBalanceChart = dynamic(() => import("@/components/dashboard/nutrition-balance-chart").then(m => m.NutritionBalanceChart), {
  loading: () => <div className="h-64 animate-pulse rounded-3xl bg-black/[0.05]" />
});
const BloodPressureChart = dynamic(() => import("@/components/dashboard/blood-pressure-chart").then(m => m.BloodPressureChart), {
  loading: () => <div className="h-64 animate-pulse rounded-3xl bg-black/[0.05]" />
});

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
  const copy = new Date(parsed);
  copy.setUTCDate(copy.getUTCDate() + days);
  return formatDateKey(copy);
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
  
  const deferredRange = useDeferredValue(range);
  const deferredCustomRange = useDeferredValue(customRange);

  // Auto-detect latest activity and set range accordingly
  // We use enabled: !!(status === "authenticated" && !autoRangeApplied) to avoid unnecessary fetches
  const { data: latestMealResult } = useQuery({
    queryKey: ["meals", "latest", 1],
    queryFn: () => listMealRecords(1),
    enabled: status === "authenticated" && !autoRangeApplied,
    staleTime: Infinity, // Range detection only needs to happen once per session/mount
  });

  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect */
    if (latestMealResult?.records?.[0] && !autoRangeApplied) {
      const record = latestMealResult.records[0];
      const raw = record.captured_at ?? record.created_at;
      const latestKey = raw ? formatDateKey(raw as string) : formatDateKey(new Date());
      setCustomRange({
        from: shiftDateKey(latestKey, -29),
        to: latestKey,
      });
      setRange("custom");
      setAutoRangeApplied(true);
    } else if (latestMealResult && !autoRangeApplied) {
      // If no records found, just mark as applied to stop trying
      setAutoRangeApplied(true);
    }
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [latestMealResult, autoRangeApplied]);

  // Main dashboard overview query
  const { 
    data: overview, 
    error: overviewError, 
    isLoading: overviewLoading,
    isPlaceholderData 
  } = useQuery({
    queryKey: ["dashboard", "overview", deferredRange, deferredCustomRange],
    queryFn: () => getDashboardOverview({
      range: deferredRange,
      from: deferredRange === "custom" ? deferredCustomRange.from : undefined,
      to: deferredRange === "custom" ? deferredCustomRange.to : undefined,
    }),
    enabled: status === "authenticated" && (deferredRange !== "custom" || (!!deferredCustomRange.from && !!deferredCustomRange.to)),
    placeholderData: (prev) => prev,
  });

  // Derived state calculated during render (rerender-derived-state-no-effect)
  const summarySparklines = useMemo(() => {
    if (!overview) return null;
    return {
      adherence: overview.charts.calories.points.map(p => ({ value: p.value })),
      risk: overview.charts.glycemic_risk.points.map(p => ({ value: p.value })),
      nutrition: overview.charts.calories.points.map(p => ({ value: p.value })),
    };
  }, [overview]);

  const error = overviewError instanceof Error ? overviewError.message : overviewError ? String(overviewError) : null;

  return (
    <div className="section-stack">
      {status === "unauthenticated" ? <ErrorCard message="Sign in to explore your health dashboard." /> : null}
      {error ? <ErrorCard message={error} /> : null}

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight" role="heading">Overview</h1>
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

      {overviewLoading && !overview ? <DashboardSkeleton /> : null}

      {overview && summarySparklines ? (
        <div className={isPlaceholderData ? "opacity-50 transition-opacity" : "relative isolate"}>
          {!isPlaceholderData && <div className="dashboard-grounding" />}
          <div className="grid grid-cols-12 gap-6">
            <MetricStrip overview={overview} sparklines={summarySparklines} />
            
            <div className="col-span-12 flex flex-col gap-6">
              <CorrelationChart 
                calories={overview.charts.calories.points} 
                risk={overview.charts.glycemic_risk.points} 
              />
            </div>

            <div className="col-span-12 lg:col-span-6">
              <NutritionBalanceChart chart={overview.charts.macros} />
            </div>
            <div className="col-span-12 lg:col-span-6">
              <MealClock bins={overview.charts.meal_timing.bins} />
            </div>
            <div className="col-span-12">
              <BloodPressureChart chart={overview?.charts.blood_pressure} loading={overviewLoading} />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
