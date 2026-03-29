"use client";

import { useEffect, useState } from "react";
import { RefreshCcw, LayoutDashboard } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ErrorCard } from "@/components/app/error-card";
import { AsyncLabel } from "@/components/app/async-label";
import { getDashboardOverview } from "@/lib/api/dashboard-client";
import type { DashboardOverviewApiResponse, RangeKey } from "@/lib/types";

import { MetricStrip } from "@/components/dashboard/metric-strip";
import { ClinicalSummary } from "@/components/dashboard/clinical-summary";
import { NutritionBalanceChart } from "@/components/dashboard/nutrition-balance-chart";
import { CorrelationChart } from "@/components/dashboard/correlation-chart";
import { MealClock } from "@/components/dashboard/meal-clock";
import { BloodPressureChart } from "@/components/dashboard/blood-pressure-chart";
import { NextActions } from "@/components/dashboard/next-actions";
import { RangeSelector } from "@/components/dashboard/range-selector";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardOverviewApiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [range, setRange] = useState<RangeKey>("30d");
  const [customRange, setCustomRange] = useState({ from: "", to: "" });

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const resp = await getDashboardOverview({ range });
      setData(resp);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, [range]);

  return (
    <div className="section-stack max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pb-12 bg-[color:var(--background)] min-h-screen">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between py-6">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <LayoutDashboard className="h-6 w-6 text-[color:var(--accent)]" />
            <h1 className="text-2xl font-extrabold tracking-tight text-[color:var(--foreground)]">Health Dashboard</h1>
          </div>
          <p className="text-xs text-[color:var(--muted-foreground)] font-medium uppercase tracking-wider">
            Patient Trends, Insights & Analytics
          </p>
        </div>
        <div className="flex items-center gap-3">
          <RangeSelector 
            range={range} 
            onRangeChange={setRange} 
            customRange={customRange}
            onCustomRangeChange={setCustomRange}
          />
          <Button
            variant="secondary"
            size="sm"
            onClick={refresh}
            disabled={loading}
            className="gap-2 rounded-xl h-11 px-4 bg-[color:var(--surface)] shadow-sm border-[color:var(--border-soft)] hover:bg-[color:var(--panel-soft)] transition-all"
          >
            <RefreshCcw className={loading ? "animate-spin h-4 w-4" : "h-4 w-4"} />
            <AsyncLabel active={loading} idle="Refresh" loading="Refreshing" />
          </Button>
        </div>
      </div>

      {error ? (
        <div className="mb-6">
          <ErrorCard message={error} />
        </div>
      ) : null}

      {data && (
        <div className="space-y-8">
          <MetricStrip overview={data} charts={data.charts} />
          
          {/* Row 1: Primary signals */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-8">
              <ClinicalSummary 
                adherence={data.summary.adherence_score.value}
                risk={data.summary.glycemic_risk.value}
                nutrition={data.summary.nutrition_goal_score.value}
                recommendation={data.insights.recommendations[0]}
              />
            </div>
            
            <div className="space-y-8">
              <div className="glass-card h-full">
                <div className="flex items-center justify-between mb-5">
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-[color:var(--muted-foreground)]">Critical alerts</p>
                    <h3 className="text-lg font-bold tracking-tight text-[color:var(--foreground)]">Immediate follow‑ups</h3>
                  </div>
                  <span className="text-[11px] font-semibold text-[color:var(--accent)]">
                    {data.alerts.length} alerts
                  </span>
                </div>
                <div className="space-y-3">
                  {data.alerts.length ? (
                    data.alerts.slice(0, 4).map((alert) => (
                      <div
                        key={alert.id}
                        className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)]/70 px-4 py-3"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-semibold text-[color:var(--foreground)]">
                            {alert.title}
                          </span>
                          <span
                            className={`text-[10px] font-semibold uppercase tracking-wider ${
                              alert.severity === "critical"
                                ? "text-rose-500"
                                : alert.severity === "warning"
                                  ? "text-amber-500"
                                  : "text-emerald-500"
                            }`}
                          >
                            {alert.severity}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-[color:var(--muted-foreground)]">
                          {alert.detail}
                        </p>
                      </div>
                    ))
                  ) : (
                    <div className="rounded-xl border border-dashed border-[color:var(--border-soft)] p-4 text-xs text-[color:var(--muted-foreground)]">
                      No critical alerts right now.
                    </div>
                  )}
                </div>
              </div>

              <NextActions 
                recommendations={data.insights.recommendations}
                links={{
                  chat: "/chat",
                  meals: data.links.meals,
                  medications: data.links.medications
                }}
              />
            </div>
          </div>

          {/* Row 2: Trends */}
          <CorrelationChart
            calories={data.charts.calories.points}
            risk={data.charts.glycemic_risk.points}
          />

          {/* Row 3: Daily patterns */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <NutritionBalanceChart chart={data.charts.macros} />
            <MealClock bins={data.charts.meal_timing.bins} />
          </div>

          {/* Row 4: Vitals */}
          <BloodPressureChart chart={data.charts.blood_pressure} />
        </div>
      )}
    </div>
  );
}
