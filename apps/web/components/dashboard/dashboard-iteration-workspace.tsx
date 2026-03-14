"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { ErrorCard } from "@/components/app/error-card";
import { useSession } from "@/components/app/session-provider";
import { SummaryStrip } from "@/components/dashboard/summary-strip";
import { RangeSelector, type RangeKey } from "@/components/dashboard/range-selector";
import { TrendPanel } from "@/components/dashboard/trend-panel";
import { ClinicalSummary } from "@/components/dashboard/clinical-summary";
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

function useChartWindow<T>(points: T[]) {
  const [windowKey, setWindowKey] = useState<"all" | "14" | "7">("all");
  useEffect(() => {
    setWindowKey("all");
  }, [points.length]);
  const windowed = useMemo(() => {
    if (windowKey === "7") return points.slice(-7);
    if (windowKey === "14") return points.slice(-14);
    return points;
  }, [points, windowKey]);
  return {
    windowKey,
    setWindowKey,
    windowed,
  };
}

function ChartWindowButtons({
  total,
  windowKey,
  onChange,
}: {
  total: number;
  windowKey: "all" | "14" | "7";
  onChange: (value: "all" | "14" | "7") => void;
}) {
  if (total <= 10) return null;
  return (
    <div className="flex items-center gap-2">
      {[
        { value: "7" as const, label: "7" },
        { value: "14" as const, label: "14" },
        { value: "all" as const, label: "All" },
      ].map((option) => (
        <button
          key={option.value}
          type="button"
          className={cn(
            "rounded-full px-2.5 py-1 text-[11px] font-semibold transition",
            windowKey === option.value
              ? "bg-[color:var(--foreground)] text-[color:var(--background)]"
              : "bg-black/5 text-[color:var(--muted-foreground)] hover:bg-black/10",
          )}
          onClick={(event) => {
            event.stopPropagation();
            onChange(option.value);
          }}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
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
  const { windowKey, setWindowKey, windowed } = useChartWindow(chart.points);
  const [activeIndex, setActiveIndex] = useState<number | null>(windowed.length ? windowed.length - 1 : null);
  useEffect(() => {
    setActiveIndex(windowed.length ? windowed.length - 1 : null);
  }, [windowed]);

  const active = activeIndex == null ? null : windowed[activeIndex] ?? null;
  const values = windowed.map((point) => point.value);
  const targets = windowed.map((point) => point.target ?? 0);
  const maxValue = Math.max(1, ...values, ...targets);
  const minValue = Math.min(...values);
  const range = Math.max(1, maxValue - Math.min(0, minValue));

  const path = windowed
    .map((point, index) => {
      const x = windowed.length === 1 ? 50 : (index / (windowed.length - 1)) * 100;
      const y = 100 - (((point.value - Math.min(0, minValue)) / range) * 84 + 8);
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");
  const targetPath = windowed
    .map((point, index) => {
      const target = point.target ?? 0;
      const x = windowed.length === 1 ? 50 : (index / (windowed.length - 1)) * 100;
      const y = 100 - (((target - Math.min(0, minValue)) / range) * 84 + 8);
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");

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
        <ChartWindowButtons total={chart.points.length} windowKey={windowKey} onChange={setWindowKey} />
      </div>
      <div className="rounded-xl border border-black/5 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(255,255,255,0.55))] p-4">
        <svg viewBox="0 0 100 100" className="h-48 w-full overflow-visible">
          {chart.title === "Glycemic Risk Trend" ? (
            <>
              <rect x="0" y="8" width="100" height="28" fill="rgba(34,197,94,0.09)" rx="4" />
              <rect x="0" y="36" width="100" height="24" fill="rgba(245,158,11,0.08)" rx="4" />
              <rect x="0" y="60" width="100" height="32" fill="rgba(239,68,68,0.08)" rx="4" />
            </>
          ) : null}
          <path d={targetPath} fill="none" stroke="rgba(100,116,139,0.4)" strokeDasharray="2.5 2.5" strokeWidth="1.2" />
          <path d={path} fill="none" stroke={tint} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
          {windowed.map((point, index) => {
            const x = windowed.length === 1 ? 50 : (index / (windowed.length - 1)) * 100;
            const y = 100 - (((point.value - Math.min(0, minValue)) / range) * 84 + 8);
            const isActive = activeIndex === index;
            return (
              <g key={`${point.bucket_start}-${point.label}`}>
                <circle
                  cx={x}
                  cy={y}
                  r={isActive ? 3.6 : 2.5}
                  fill={isActive ? tint : "white"}
                  stroke={tint}
                  strokeWidth="1.5"
                  className="cursor-pointer transition"
                  onMouseEnter={() => setActiveIndex(index)}
                />
              </g>
            );
          })}
        </svg>
        <div className="mt-3 grid grid-cols-4 gap-2 text-[11px] uppercase tracking-[0.18em] text-[color:var(--muted-foreground)]">
          {windowed.filter((_, index) => index === 0 || index === windowed.length - 1 || index === Math.floor(windowed.length / 2)).map((point) => (
            <div key={point.bucket_start}>{point.label}</div>
          ))}
        </div>
      </div>
    </div>
  );
}

function MacroStackChart({ chart }: { chart: DashboardMacroChartApi }) {
  const { windowKey, setWindowKey, windowed } = useChartWindow(chart.points);
  const [activeIndex, setActiveIndex] = useState<number | null>(windowed.length ? windowed.length - 1 : null);
  useEffect(() => {
    setActiveIndex(windowed.length ? windowed.length - 1 : null);
  }, [windowed]);
  const active = activeIndex == null ? null : windowed[activeIndex] ?? null;
  const maxCalories = Math.max(1, ...windowed.map((point) => point.calories));

  return (
    <section className="metric-card">
      <div className="text-sm font-semibold text-[color:var(--foreground)]">{chart.title}</div>
      <p className="mt-1 text-xs text-[color:var(--muted-foreground)]">
        Macro composition by period.
      </p>
      <div className="mt-4 space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3 text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)]">
            <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-[#d97706]" />Protein</span>
            <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-[#0f766e]" />Carbs</span>
            <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-[#7c3aed]" />Fats</span>
          </div>
          <ChartWindowButtons total={chart.points.length} windowKey={windowKey} onChange={setWindowKey} />
        </div>
        {active ? (
          <div className="rounded-xl bg-black/[0.03] px-3 py-2 text-xs text-[color:var(--muted-foreground)]">
            <span className="font-semibold text-[color:var(--foreground)]">{active.label}</span>
            {` `}
            {`${Math.round(active.protein_g)}g protein, ${Math.round(active.carbs_g)}g carbs, ${Math.round(active.fat_g)}g fats`}
          </div>
        ) : null}
        <div className="flex h-56 items-end gap-2 rounded-xl border border-black/5 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(255,255,255,0.55))] px-3 pb-3 pt-5">
          {windowed.map((point, index) => {
            const height = `${Math.max(8, (point.calories / maxCalories) * 100)}%`;
            const total = Math.max(1, point.protein_g + point.carbs_g + point.fat_g);
            return (
              <button
                key={point.bucket_start}
                type="button"
                className="flex flex-1 flex-col items-center gap-2"
                onMouseEnter={() => setActiveIndex(index)}
              >
                <div className={cn("flex w-full flex-col overflow-hidden rounded-t-lg rounded-b-sm border border-black/5", activeIndex === index && "ring-2 ring-[color:var(--foreground)]/10")}>
                  <div style={{ height, display: "flex", flexDirection: "column", justifyContent: "flex-end" }}>
                    <div style={{ height: `${(point.protein_g / total) * 100}%` }} className="bg-[#d97706]" />
                    <div style={{ height: `${(point.carbs_g / total) * 100}%` }} className="bg-[#0f766e]" />
                    <div style={{ height: `${(point.fat_g / total) * 100}%` }} className="bg-[#7c3aed]" />
                  </div>
                </div>
                <span className="text-[10px] font-bold uppercase tracking-tighter text-[color:var(--muted-foreground)] opacity-60">{point.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function MealTimingHistogram({ chart }: { chart: DashboardMealTimingChartApi }) {
  const peak = Math.max(1, ...chart.bins.map((item) => item.count));
  const [activeHour, setActiveHour] = useState<number | null>(null);
  const active = activeHour == null ? null : chart.bins.find((item) => item.hour === activeHour) ?? null;
  return (
    <section className="metric-card">
      <div className="text-sm font-semibold text-[color:var(--foreground)]">{chart.title}</div>
      <p className="mt-1 text-xs text-[color:var(--muted-foreground)]">
        Meal density distribution.
      </p>
      <div className="mt-4 space-y-4">
        <div className="rounded-xl bg-black/[0.03] px-3 py-2 text-xs text-[color:var(--muted-foreground)]">
          {active ? (
            <>
              <span className="font-semibold text-[color:var(--foreground)]">{active.label}</span>
              {` `}
              {`${active.count} meals logged`}
            </>
          ) : (
            "Hover bars to inspect density."
          )}
        </div>
        <div className="grid h-56 grid-cols-12 items-end gap-1.5 rounded-xl border border-black/5 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(255,255,255,0.55))] p-3 sm:grid-cols-24">
          {chart.bins.map((item) => (
            <button key={item.hour} type="button" className="flex h-full flex-col justify-end gap-1.5" onMouseEnter={() => setActiveHour(item.hour)}>
              <div
                className={cn(
                  "rounded-t-lg rounded-b-sm bg-[linear-gradient(180deg,#0f766e,#164e63)] transition",
                  activeHour === item.hour ? "opacity-100 shadow-sm" : "opacity-70",
                )}
                style={{ height: `${Math.max(6, (item.count / peak) * 100)}%` }}
              />
              <span className="text-[9px] font-bold text-[color:var(--muted-foreground)] opacity-50">{item.hour}</span>
            </button>
          ))}
        </div>
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
        <>
          <ClinicalSummary
            adherence={overview.summary.adherence_score.value}
            risk={overview.summary.glycemic_risk.value}
            nutrition={overview.summary.nutrition_goal_score.value}
            recommendation={overview.insights.recommendations[0] ?? "Keep tracking your meals to reveal deeper insights."}
          />

          <div className="page-grid">
            <div className="space-y-8">
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
            </div>

            <div className="space-y-8">
              <SummaryStrip
                metrics={[
                  overview.summary.adherence_score,
                  overview.summary.glycemic_risk,
                  overview.summary.nutrition_goal_score,
                ]}
              />
              <MacroStackChart chart={overview.charts.macros} />
              <MealTimingHistogram chart={overview.charts.meal_timing} />
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
