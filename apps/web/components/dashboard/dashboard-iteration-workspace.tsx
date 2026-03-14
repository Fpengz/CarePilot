"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";

import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { useSession } from "@/components/app/session-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { getDashboardOverview } from "@/lib/api/dashboard-client";
import type {
  DashboardMacroChartApi,
  DashboardMealTimingChartApi,
  DashboardMetricChartApi,
  DashboardOverviewApiResponse,
  DashboardSummaryMetricApi,
} from "@/lib/types";
import { cn } from "@/lib/utils";

type RangeKey = "today" | "7d" | "30d" | "3m" | "1y" | "custom";

const RANGE_OPTIONS: Array<{ value: RangeKey; label: string }> = [
  { value: "today", label: "Today" },
  { value: "7d", label: "Last 7 Days" },
  { value: "30d", label: "Last 30 Days" },
  { value: "3m", label: "Last 3 Months" },
  { value: "1y", label: "Last Year" },
  { value: "custom", label: "Custom Range" },
];

function getDefaultCustomRange() {
  const to = new Date();
  const from = new Date(to);
  from.setDate(to.getDate() - 29);
  return {
    from: from.toISOString().slice(0, 10),
    to: to.toISOString().slice(0, 10),
  };
}

function formatMetric(metric: DashboardSummaryMetricApi): string {
  if (metric.unit === "%") return `${Math.round(metric.value)}%`;
  if (metric.unit === "/100") return `${Math.round(metric.value)}/100`;
  return `${Math.round(metric.value)}${metric.unit ? ` ${metric.unit}` : ""}`;
}

function formatSigned(value: number, suffix = ""): string {
  const rounded = Math.round(value * 10) / 10;
  if (rounded === 0) return `0${suffix}`;
  return `${rounded > 0 ? "+" : ""}${rounded}${suffix}`;
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

function SummaryCard({ metric, accent }: { metric: DashboardSummaryMetricApi; accent: string }) {
  return (
    <div
      className="relative overflow-hidden rounded-[26px] border border-black/10 bg-[color:var(--panel)] p-5 shadow-[0_24px_60px_rgba(15,23,42,0.08)]"
      style={{
        backgroundImage: `linear-gradient(145deg, color-mix(in oklab, ${accent} 20%, white) 0%, rgba(255,255,255,0.92) 58%)`,
      }}
    >
      <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[color:var(--muted-foreground)]">{metric.label}</div>
      <div className="mt-3 flex items-end justify-between gap-3">
        <div className="text-3xl font-semibold tracking-tight text-[color:var(--foreground)]">{formatMetric(metric)}</div>
        <div
          className={cn(
            "rounded-full px-2.5 py-1 text-xs font-semibold",
            metric.direction === "up"
              ? "bg-emerald-500/12 text-emerald-700"
              : metric.direction === "down"
                ? "bg-amber-500/12 text-amber-700"
                : "bg-slate-500/10 text-slate-600",
          )}
        >
          {formatSigned(metric.delta, metric.unit === "%" ? "%" : "")}
        </div>
      </div>
      {metric.status ? (
        <div className="mt-3 inline-flex rounded-full bg-white/80 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-foreground)]">
          {metric.status}
        </div>
      ) : null}
      {metric.detail ? <p className="mt-3 max-w-[30ch] text-sm leading-6 text-[color:var(--muted-foreground)]">{metric.detail}</p> : null}
    </div>
  );
}

function ChartShell({
  title,
  description,
  href,
  children,
}: {
  title: string;
  description: string;
  href: string;
  children: import("react").ReactNode;
}) {
  const router = useRouter();
  return (
    <Card
      className="group cursor-pointer overflow-hidden border-black/10 bg-[color:var(--panel)] shadow-[0_22px_60px_rgba(15,23,42,0.08)] transition hover:-translate-y-0.5 hover:shadow-[0_28px_70px_rgba(15,23,42,0.11)]"
      onClick={() => router.push(href)}
    >
      <CardHeader className="border-b border-black/5 bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(255,255,255,0.55))]">
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle className="text-base">{title}</CardTitle>
            <CardDescription className="mt-2 max-w-[42ch] text-sm leading-6">{description}</CardDescription>
          </div>
          <span className="rounded-full bg-black/5 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-foreground)]">
            Open
          </span>
        </div>
      </CardHeader>
      <CardContent className="p-5">{children}</CardContent>
    </Card>
  );
}

function MetricLineChart({
  chart,
  href,
  tint,
  detailLabel,
}: {
  chart: DashboardMetricChartApi;
  href: string;
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
    <ChartShell title={chart.title} description={`${detailLabel} Hover to inspect values. Use the window controls to zoom into smaller slices.`} href={href}>
      <div className="space-y-4" onClick={(event) => event.stopPropagation()}>
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
        <div className="rounded-[22px] border border-black/5 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(255,255,255,0.55))] p-4">
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
    </ChartShell>
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
    <ChartShell title={chart.title} description="Macro composition by time bucket. Hover bars to inspect protein, carbs, and fats for any period." href="/meals">
      <div className="space-y-4" onClick={(event) => event.stopPropagation()}>
        <div className="flex items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3 text-xs text-[color:var(--muted-foreground)]">
            <span className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-[#d97706]" />Protein</span>
            <span className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-[#0f766e]" />Carbs</span>
            <span className="inline-flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full bg-[#7c3aed]" />Fats</span>
          </div>
          <ChartWindowButtons total={chart.points.length} windowKey={windowKey} onChange={setWindowKey} />
        </div>
        {active ? (
          <div className="rounded-2xl bg-black/[0.03] px-4 py-3 text-sm text-[color:var(--muted-foreground)]">
            <span className="font-semibold text-[color:var(--foreground)]">{active.label}</span>
            {` `}
            {`${Math.round(active.protein_g)}g protein, ${Math.round(active.carbs_g)}g carbs, ${Math.round(active.fat_g)}g fats`}
          </div>
        ) : null}
        <div className="flex h-64 items-end gap-3 rounded-[24px] border border-black/5 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(255,255,255,0.55))] px-4 pb-4 pt-6">
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
                <div className={cn("flex w-full flex-col overflow-hidden rounded-t-[16px] rounded-b-[10px] border border-black/5", activeIndex === index && "ring-2 ring-[color:var(--foreground)]/15")}>
                  <div style={{ height, display: "flex", flexDirection: "column", justifyContent: "flex-end" }}>
                    <div style={{ height: `${(point.protein_g / total) * 100}%` }} className="bg-[#d97706]" />
                    <div style={{ height: `${(point.carbs_g / total) * 100}%` }} className="bg-[#0f766e]" />
                    <div style={{ height: `${(point.fat_g / total) * 100}%` }} className="bg-[#7c3aed]" />
                  </div>
                </div>
                <span className="text-[11px] font-medium uppercase tracking-[0.12em] text-[color:var(--muted-foreground)]">{point.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </ChartShell>
  );
}

function MealTimingHistogram({ chart }: { chart: DashboardMealTimingChartApi }) {
  const peak = Math.max(1, ...chart.bins.map((item) => item.count));
  const [activeHour, setActiveHour] = useState<number | null>(null);
  const active = activeHour == null ? null : chart.bins.find((item) => item.hour === activeHour) ?? null;
  return (
    <ChartShell title={chart.title} description="When meals are being logged across the day. Click into Meals for the full event list and corrections." href="/meals">
      <div className="space-y-4" onClick={(event) => event.stopPropagation()}>
        <div className="rounded-2xl bg-black/[0.03] px-4 py-3 text-sm text-[color:var(--muted-foreground)]">
          {active ? (
            <>
              <span className="font-semibold text-[color:var(--foreground)]">{active.label}</span>
              {` `}
              {`${active.count} meals logged`}
            </>
          ) : (
            "Hover over a bar to inspect meal density by hour."
          )}
        </div>
        <div className="grid h-56 grid-cols-12 items-end gap-2 rounded-[24px] border border-black/5 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(255,255,255,0.55))] p-4 sm:grid-cols-24">
          {chart.bins.map((item) => (
            <button key={item.hour} type="button" className="flex h-full flex-col justify-end gap-2" onMouseEnter={() => setActiveHour(item.hour)}>
              <div
                className={cn(
                  "rounded-t-[14px] rounded-b-[10px] bg-[linear-gradient(180deg,#0f766e,#164e63)] transition",
                  activeHour === item.hour ? "opacity-100 shadow-[0_12px_24px_rgba(15,118,110,0.25)]" : "opacity-75",
                )}
                style={{ height: `${Math.max(6, (item.count / peak) * 100)}%` }}
              />
              <span className="text-[10px] font-medium uppercase tracking-[0.12em] text-[color:var(--muted-foreground)]">{item.hour}</span>
            </button>
          ))}
        </div>
      </div>
    </ChartShell>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="h-40 animate-pulse rounded-[26px] bg-black/[0.05]" />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="h-96 animate-pulse rounded-[26px] bg-black/[0.05]" />
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

  const headline = overview?.range.label ?? RANGE_OPTIONS.find((item) => item.value === range)?.label ?? "Dashboard";

  return (
    <div className="space-y-7">
      <PageTitle
        eyebrow="Dashboard"
        title="Health status in one scan"
        description="Track nutrition, glycemic risk, medication adherence, and meal rhythm with one shared date range."
        tags={overview ? [headline, `${overview.range.bucket} view`] : ["analytics"]}
      />

      {status === "unauthenticated" ? <ErrorCard message="Sign in to explore your health dashboard." /> : null}
      {error ? <ErrorCard message={error} /> : null}

      <section className="overflow-hidden rounded-[32px] border border-black/10 bg-[linear-gradient(135deg,rgba(255,250,241,0.94),rgba(241,248,247,0.9)_48%,rgba(245,248,255,0.92))] p-5 shadow-[0_32px_80px_rgba(15,23,42,0.08)] sm:p-7">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
          <div className="space-y-5">
            <div className="max-w-[56ch]">
              <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[color:var(--muted-foreground)]">Live Overview</div>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight text-[color:var(--foreground)] sm:text-4xl">See what changed before you leave the page.</h2>
              <p className="mt-3 text-sm leading-7 text-[color:var(--muted-foreground)]">
                The dashboard rescales every chart to the selected window and keeps the most important clinical signals in view.
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-4">
              <SummaryCard metric={overview?.summary.nutrition_goal_score ?? { label: "Nutrition Goal Score", value: 0, unit: "%", delta: 0, direction: "flat" }} accent="#f59e0b" />
              <SummaryCard metric={overview?.summary.adherence_score ?? { label: "Adherence Score", value: 0, unit: "%", delta: 0, direction: "flat" }} accent="#0f766e" />
              <SummaryCard metric={overview?.summary.glycemic_risk ?? { label: "Glycemic Risk", value: 0, unit: "/100", delta: 0, direction: "flat" }} accent="#ef4444" />
              <SummaryCard metric={overview?.summary.stability_index ?? { label: "Stability Index", value: 0, unit: "%", delta: 0, direction: "flat" }} accent="#2563eb" />
            </div>
          </div>

          <Card className="border-black/10 bg-white/75 shadow-none backdrop-blur">
            <CardHeader>
              <CardTitle className="text-base">Time Range</CardTitle>
              <CardDescription>All cards and charts update together. Longer windows automatically roll up to weekly averages.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3">
                <Select
                  value={range}
                  onChange={(event) => {
                    const nextRange = event.target.value as RangeKey;
                    startTransition(() => setRange(nextRange));
                  }}
                >
                  {RANGE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </Select>

                {range === "custom" ? (
                  <div className="grid gap-3 sm:grid-cols-2">
                    <label className="space-y-2 text-sm">
                      <span className="font-medium text-[color:var(--foreground)]">From</span>
                      <Input
                        type="date"
                        value={customRange.from}
                        onChange={(event) =>
                          startTransition(() => setCustomRange((current) => ({ ...current, from: event.target.value })))
                        }
                      />
                    </label>
                    <label className="space-y-2 text-sm">
                      <span className="font-medium text-[color:var(--foreground)]">To</span>
                      <Input
                        type="date"
                        value={customRange.to}
                        onChange={(event) =>
                          startTransition(() => setCustomRange((current) => ({ ...current, to: event.target.value })))
                        }
                      />
                    </label>
                  </div>
                ) : null}
              </div>

              {overview ? (
                <div className="rounded-[22px] border border-black/5 bg-black/[0.03] p-4 text-sm text-[color:var(--muted-foreground)]">
                  <div className="font-semibold text-[color:var(--foreground)]">{overview.range.label}</div>
                  <div className="mt-1">
                    {formatDateLabel(overview.range.from)} to {formatDateLabel(overview.range.to)}
                  </div>
                  <div className="mt-2">Aggregation: {overview.range.bucket === "hour" ? "hourly" : overview.range.bucket === "day" ? "daily" : "weekly averages"}</div>
                </div>
              ) : null}

              <div className="grid gap-3">
                {(overview?.alerts ?? []).slice(0, 3).map((alert) => (
                  <div
                    key={alert.id}
                    className={cn(
                      "rounded-[20px] border px-4 py-3",
                      alert.severity === "critical"
                        ? "border-red-200 bg-red-50"
                        : alert.severity === "warning"
                          ? "border-amber-200 bg-amber-50"
                          : "border-sky-200 bg-sky-50",
                    )}
                  >
                    <div className="text-sm font-semibold text-[color:var(--foreground)]">{alert.title}</div>
                    <p className="mt-1 text-sm leading-6 text-[color:var(--muted-foreground)]">{alert.detail}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {loading && !overview ? <DashboardSkeleton /> : null}

      {overview ? (
        <>
          <div className="grid gap-6 xl:grid-cols-2">
            <MetricLineChart chart={overview.charts.calories} href={overview.links.meals} tint="#c2410c" detailLabel="Calories logged" />
            <MetricLineChart chart={overview.charts.glycemic_risk} href={overview.links.metrics} tint="#dc2626" detailLabel="Risk score" />
            <MacroStackChart chart={overview.charts.macros} />
            <MetricLineChart chart={overview.charts.adherence} href={overview.links.medications} tint="#0f766e" detailLabel="Adherence rate" />
          </div>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
            <MealTimingHistogram chart={overview.charts.meal_timing} />

            <Card className="overflow-hidden border-black/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.95),rgba(247,248,251,0.92))] shadow-[0_22px_60px_rgba(15,23,42,0.08)]">
              <CardHeader>
                <CardTitle className="text-base">Insights and next moves</CardTitle>
                <CardDescription>AI-facing takeaways distilled into concrete actions for the selected window.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="rounded-[22px] border border-black/5 bg-[#f7f4ee] p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[color:var(--muted-foreground)]">Recommendations</div>
                  <div className="mt-3 space-y-3">
                    {overview.insights.recommendations.map((item) => (
                      <div key={item} className="rounded-2xl bg-white/90 px-4 py-3 text-sm leading-6 text-[color:var(--foreground)]">
                        {item}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-[22px] border border-black/5 bg-[#eef6f5] p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[color:var(--muted-foreground)]">Key drivers</div>
                  <div className="mt-3 space-y-3">
                    {overview.insights.key_drivers.map((item) => (
                      <div key={item} className="rounded-2xl bg-white/90 px-4 py-3 text-sm leading-6 text-[color:var(--foreground)]">
                        {item}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <Button asChild className="h-11">
                    <Link href={overview.links.meals}>Open meal analytics</Link>
                  </Button>
                  <Button asChild variant="secondary" className="h-11">
                    <Link href={overview.links.medications}>Review medication adherence</Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </>
      ) : null}
    </div>
  );
}
