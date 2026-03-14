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

function MetricLineChart({
  chart,
  tint,
  detailLabel,
}: {
  chart: DashboardMetricChartApi;
  tint: string;
  detailLabel: string;
}) {
  const windowed = chart.points;
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
      </div>
      <div className="rounded-xl border border-[color:var(--chart-grid)] bg-[linear-gradient(180deg,var(--chart-gradient-start),var(--chart-gradient-end))] p-4">
        <svg viewBox="0 0 100 100" className="h-48 w-full overflow-visible">
          {chart.title === "Glycemic Risk Trend" ? (
            <>
              <rect x="0" y="8" width="100" height="28" fill="var(--chart-grid)" fillOpacity="0.2" rx="4" />
              <rect x="0" y="36" width="100" height="24" fill="var(--chart-grid)" fillOpacity="0.15" rx="4" />
              <rect x="0" y="60" width="100" height="32" fill="var(--chart-grid)" fillOpacity="0.1" rx="4" />
            </>
          ) : null}
          <path d={targetPath} fill="none" stroke="var(--chart-text)" strokeDasharray="2.5 2.5" strokeWidth="1.2" strokeOpacity="0.4" />
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
                  fill={isActive ? tint : "var(--chart-bg)"}
                  stroke={tint}
                  strokeWidth="1.5"
                  className="cursor-pointer transition"
                  onMouseEnter={() => setActiveIndex(index)}
                />
              </g>
            );
          })}
        </svg>
        <div className="mt-3 flex justify-between text-[10px] font-bold uppercase tracking-[0.1em] text-[color:var(--chart-text)]">
          {windowed.length > 0 && <div>{windowed[0].label}</div>}
          {windowed.length > 2 && <div className="hidden sm:block">{windowed[Math.floor(windowed.length / 2)].label}</div>}
          {windowed.length > 1 && <div>{windowed[windowed.length - 1].label}</div>}
        </div>
      </div>
    </div>
  );
}

function MacroStackChart({ chart }: { chart: DashboardMacroChartApi }) {
  const windowed = chart.points;
  const [activeIndex, setActiveIndex] = useState<number | null>(windowed.length ? windowed.length - 1 : null);
  useEffect(() => {
    setActiveIndex(windowed.length ? windowed.length - 1 : null);
  }, [windowed]);
  const active = activeIndex == null ? null : windowed[activeIndex] ?? null;
  const maxCalories = Math.max(1, ...windowed.map((point) => point.calories));
  const isScrollable = windowed.length > 14;

  return (
    <section className="metric-card">
      <div className="flex items-center justify-between gap-4">
        <div className="text-sm font-semibold text-[color:var(--foreground)]">{chart.title}</div>
        <div className="flex flex-wrap items-center gap-2 text-[9px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)]">
          <span className="inline-flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-[#d97706]" />P</span>
          <span className="inline-flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-[#0f766e]" />C</span>
          <span className="inline-flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full bg-[#7c3aed]" />F</span>
        </div>
      </div>
      <p className="mt-1 text-xs text-[color:var(--muted-foreground)]">
        Daily macro balance across the selected period.
      </p>
      <div className="mt-4 space-y-4">
        {active ? (
          <div className="rounded-xl bg-black/[0.03] dark:bg-white/[0.03] px-3 py-2 text-xs text-[color:var(--muted-foreground)] animate-in fade-in duration-300">
            <span className="font-semibold text-[color:var(--foreground)]">{active.label}</span>
            {` — `}
            {`${Math.round(active.protein_g)}g Prot, ${Math.round(active.carbs_g)}g Carb, ${Math.round(active.fat_g)}g Fat`}
          </div>
        ) : (
          <div className="h-8" />
        )}
        
        <div className={cn(
          "rounded-xl border border-[color:var(--chart-grid)] bg-[linear-gradient(180deg,var(--chart-gradient-start),var(--chart-gradient-end))] px-3 pb-3 pt-5",
          isScrollable ? "overflow-x-auto scrollbar-hide" : ""
        )}>
          <div 
            className="flex h-56 items-end gap-1.5"
            style={{ 
              minWidth: isScrollable ? `${windowed.length * 24}px` : '100%',
              justifyContent: isScrollable ? 'flex-start' : 'space-between'
            }}
          >
            {windowed.map((point, index) => {
              const height = `${Math.max(8, (point.calories / maxCalories) * 100)}%`;
              const total = Math.max(1, point.protein_g + point.carbs_g + point.fat_g);
              const showLabel = windowed.length <= 14 || index === 0 || index === windowed.length - 1 || index % 7 === 0;
              
              return (
                <button
                  key={point.bucket_start}
                  type="button"
                  className={cn(
                    "flex flex-col items-center gap-2 h-full justify-end transition-opacity duration-200",
                    isScrollable ? "w-5" : "flex-1",
                    activeIndex !== null && activeIndex !== index ? "opacity-60" : "opacity-100"
                  )}
                  onMouseEnter={() => setActiveIndex(index)}
                >
                  <div className={cn(
                    "flex w-full flex-col overflow-hidden rounded-t-lg rounded-b-sm border border-[color:var(--chart-grid)]", 
                    activeIndex === index && "ring-2 ring-[color:var(--foreground)]/10 ring-offset-1 dark:ring-offset-black"
                  )}>
                    <div style={{ height, display: "flex", flexDirection: "column", justifyContent: "flex-end" }}>
                      <div style={{ height: `${(point.protein_g / total) * 100}%` }} className="bg-[#d97706]" />
                      <div style={{ height: `${(point.carbs_g / total) * 100}%` }} className="bg-[#0f766e]" />
                      <div style={{ height: `${(point.fat_g / total) * 100}%` }} className="bg-[#7c3aed]" />
                    </div>
                  </div>
                  {showLabel ? (
                    <span className="text-[9px] font-bold uppercase tracking-tighter text-[color:var(--chart-text)] opacity-60 truncate w-full text-center">{point.label}</span>
                  ) : (
                    <div className="h-1.5 w-px bg-[color:var(--chart-grid)] opacity-40" />
                  )}
                </button>
              );
            })}
          </div>
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
        Frequency distribution of meals across the 24-hour cycle.
      </p>
      <div className="mt-4 space-y-4">
        <div className="rounded-xl bg-black/[0.03] dark:bg-white/[0.03] px-3 py-2 text-xs text-[color:var(--muted-foreground)]">
          {active ? (
            <>
              <span className="font-semibold text-[color:var(--foreground)]">{active.label}</span>
              {` — `}
              {`${active.count} meals recorded`}
            </>
          ) : (
            "Hover to inspect hourly density."
          )}
        </div>
        <div className="overflow-x-auto scrollbar-hide rounded-xl border border-[color:var(--chart-grid)] bg-[linear-gradient(180deg,var(--chart-gradient-start),var(--chart-gradient-end))] p-3">
          <div className="grid h-56 min-w-[480px] grid-cols-24 items-end gap-1.5">
            {chart.bins.map((item) => (
              <button key={item.hour} type="button" className="flex h-full flex-col justify-end gap-1.5" onMouseEnter={() => setActiveHour(item.hour)}>
                <div
                  className={cn(
                    "rounded-t-lg rounded-b-sm bg-[linear-gradient(180deg,#0f766e,#164e63)] transition-all",
                    activeHour === item.hour ? "opacity-100 shadow-sm scale-x-110" : "opacity-70",
                  )}
                  style={{ height: `${Math.max(6, (item.count / peak) * 100)}%` }}
                />
                <span className={cn(
                  "text-[9px] font-bold text-[color:var(--chart-text)] transition-opacity",
                  item.hour % 4 === 0 ? "opacity-60" : "opacity-30"
                )}>{item.hour}</span>
              </button>
            ))}
          </div>
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
