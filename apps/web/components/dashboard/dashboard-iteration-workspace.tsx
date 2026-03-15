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
import { SummaryStrip } from "@/components/dashboard/summary-strip";
import { RangeSelector, type RangeKey } from "@/components/dashboard/range-selector";
import { TrendPanel } from "@/components/dashboard/trend-panel";
import { ClinicalSummary } from "@/components/dashboard/clinical-summary";
import { NutritionBalanceChart } from "@/components/dashboard/nutrition-balance-chart";
import { CHART_COLORS, COMMON_AXIS_PROPS, ClinicalTooltip } from "./chart-utils";
import { getDashboardOverview } from "@/lib/api/dashboard-client";
import type {
  DashboardMacroChartApi,
  DashboardMealTimingChartApi,
  DashboardMetricChartApi,
  DashboardOverviewApiResponse,
} from "@/lib/types";
import { cn } from "@/lib/utils";

function getDefaultCustomRange() {
  const to = new Date();
  const from = new Date(to);
  from.setDate(to.getDate() - 29);
  return {
    from: from.toISOString().slice(0, 10),
    to: to.toISOString().slice(0, 10),
  };
}

function formatDateLabel(value: string): string {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(new Date(`${value}T00:00:00`));
}

function MetricLineChart({
  chart,
  tint,
  detailLabel,
}: {
  chart: DashboardMetricChartApi;
  tint: string;
  detailLabel: string;
}) {
  const data = chart.points;
  const active = data[data.length - 1];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="text-2xl font-semibold tracking-tight text-[color:var(--foreground)]">
            {active ? Math.round(active.value) : 0}
          </div>
          <div className="mt-1 text-sm text-[color:var(--muted-foreground)]">
            {active ? `${active.label} ${detailLabel.toLowerCase()}` : "No data"}
          </div>
        </div>
      </div>
      <div className="h-48 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--chart-grid)" strokeOpacity={0.4} />
            <XAxis dataKey="label" {...COMMON_AXIS_PROPS} tickMargin={10} />
            <YAxis {...COMMON_AXIS_PROPS} tickMargin={10} />
            <Tooltip content={<ClinicalTooltip />} />
            {data.some((p) => p.target !== undefined && p.target !== null) && (
              <Line
                type="monotone"
                dataKey="target"
                name="Target"
                stroke="var(--chart-text)"
                strokeDasharray="3 3"
                strokeOpacity={0.4}
                dot={false}
              />
            )}
            <Line
              type="monotone"
              dataKey="value"
              name="Value"
              stroke={tint}
              strokeWidth={3}
              dot={{ r: 3, fill: tint, strokeWidth: 0 }}
              activeDot={{ r: 5, fill: tint, stroke: "var(--background)", strokeWidth: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function MealTimingHistogram({ chart }: { chart: DashboardMealTimingChartApi }) {
  return (
    <section className="metric-card">
      <div className="text-sm font-semibold text-[color:var(--foreground)]">{chart.title}</div>
      <p className="mt-1 text-xs text-[color:var(--muted-foreground)]">
        Frequency distribution of meals across the 24-hour cycle.
      </p>
      <div className="mt-6 h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chart.bins} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--chart-grid)" strokeOpacity={0.4} />
            <XAxis dataKey="hour" {...COMMON_AXIS_PROPS} tickMargin={10} />
            <YAxis {...COMMON_AXIS_PROPS} tickMargin={10} />
            <Tooltip
              content={<ClinicalTooltip />}
              cursor={{ fill: "var(--chart-grid)", fillOpacity: 0.1 }}
            />
            <Bar
              dataKey="count"
              name="Meals"
              fill="var(--primary)"
              radius={[4, 4, 0, 0]}
              className="fill-[color:var(--foreground)] opacity-70"
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function DashboardSkeleton() {
  return (
    <div className="section-stack">
      <div className="h-64 animate-pulse rounded-2xl bg-black/[0.05]" />
      <div className="grid gap-8 lg:grid-cols-2">
        <div className="space-y-8">
          <div className="h-96 animate-pulse rounded-xl bg-black/[0.05]" />
          <div className="h-96 animate-pulse rounded-xl bg-black/[0.05]" />
        </div>
        <div className="space-y-8">
          <div className="h-40 animate-pulse rounded-xl bg-black/[0.05]" />
          <div className="h-96 animate-pulse rounded-xl bg-black/[0.05]" />
          <div className="h-96 animate-pulse rounded-xl bg-black/[0.05]" />
        </div>
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

      {overview ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 auto-rows-min">
          <ClinicalSummary
            adherence={overview.summary.adherence_score.value}
            risk={overview.summary.glycemic_risk.value}
            nutrition={overview.summary.nutrition_goal_score.value}
            recommendation={overview.insights.recommendations[0] ?? "Keep tracking your meals to reveal deeper insights."}
          />

          <TrendPanel
            title={overview.charts.calories.title}
            description="Calories logged by period."
          >
            <MetricLineChart chart={overview.charts.calories} tint="#c2410c" detailLabel="Calories logged" />
          </TrendPanel>
          
          <TrendPanel
            title={overview.charts.glycemic_risk.title}
            description="Risk score over time with threshold bands."
          >
            <MetricLineChart chart={overview.charts.glycemic_risk} tint="#dc2626" detailLabel="Risk score" />
          </TrendPanel>

          <SummaryStrip
            metrics={[
              overview.summary.adherence_score,
              overview.summary.glycemic_risk,
              overview.summary.nutrition_goal_score,
            ]}
          />
          <NutritionBalanceChart chart={overview.charts.macros} />
          <MealTimingHistogram chart={overview.charts.meal_timing} />
        </div>
      ) : null}
    </div>
  );
}
