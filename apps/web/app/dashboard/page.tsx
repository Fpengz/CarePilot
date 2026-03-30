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
    <div className="section-stack max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pb-12 bg-background min-h-screen">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between py-10">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <LayoutDashboard className="h-8 w-8 text-accent-teal" />
            <h1 className="text-h1 font-display tracking-tight text-foreground">Health Dashboard</h1>
          </div>
          <p className="text-sm text-muted-foreground font-medium max-w-2xl">
            Monitor your vital trends, nutritional balance, and clinical insights in one place.
          </p>
        </div>
        <div className="flex items-center gap-3 pb-1">
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
            className="gap-2 rounded-xl h-11 px-4 bg-surface shadow-sm border-border-soft hover:bg-panel transition-all"
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
              <div className="bg-panel border border-border-soft rounded-3xl p-6 shadow-sm h-full">
                <div className="flex items-center justify-between mb-5 px-1">
                  <div className="space-y-1">
                    <p className="text-micro-label text-muted-foreground uppercase">Alert Status</p>
                    <h3 className="text-xl font-semibold tracking-tight text-foreground">Critical follow‑ups</h3>
                  </div>
                  <span className="text-[11px] font-semibold text-accent-teal">
                    {data.alerts.length} alerts
                  </span>
                </div>
                <div className="space-y-3">
                  {data.alerts.length ? (
                    data.alerts.slice(0, 4).map((alert) => (
                      <div
                        key={alert.id}
                        className="rounded-2xl border border-border-soft bg-surface px-4 py-3 shadow-sm"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-semibold text-foreground">
                            {alert.title}
                          </span>
                          <span
                            className={`text-[10px] font-bold uppercase tracking-wider ${
                              alert.severity === "critical"
                                ? "text-rose-600"
                                : alert.severity === "warning"
                                  ? "text-amber-600"
                                  : "text-emerald-600"
                            }`}
                          >
                            {alert.severity}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                          {alert.detail}
                        </p>
                      </div>
                    ))
                  ) : (
                    <div className="rounded-2xl border border-dashed border-border-soft p-6 text-center text-xs text-muted-foreground">
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

          {/* Row 2: Daily Rhythms */}
          <section className="space-y-6">
            <div className="flex items-baseline gap-3">
              <h2 className="text-h2 font-display text-foreground">Daily Rhythms & Balance</h2>
              <p className="text-sm text-muted-foreground">Correlating activity, nutrition, and metabolic response</p>
            </div>
            
            <div className="grid grid-cols-1 gap-8">
              <CorrelationChart
                calories={data.charts.calories.points}
                risk={data.charts.glycemic_risk.points}
              />

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <NutritionBalanceChart chart={data.charts.macros} />
                <MealClock bins={data.charts.meal_timing.bins} />
              </div>
            </div>
          </section>

          {/* Row 3: Vitals */}
          <section className="space-y-6 pt-4">
            <div className="flex items-baseline gap-3 border-t border-border-soft pt-10">
              <h2 className="text-h2 font-display text-foreground">Baseline Vitals</h2>
              <p className="text-sm text-muted-foreground">Longitudinal tracking of clinical markers</p>
            </div>
            <BloodPressureChart chart={data.charts.blood_pressure} />
          </section>
        </div>
      )}
    </div>
  );
}
