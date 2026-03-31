"use client";

import { useEffect, useState } from "react";
import { RefreshCcw, LayoutDashboard } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ErrorCard } from "@/components/app/error-card";
import { AsyncLabel } from "@/components/app/async-label";
import { getDashboardOverview } from "@/lib/api/dashboard-client";
import type { DashboardOverviewApiResponse, RangeKey } from "@/lib/types";

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
    <main className="section-stack max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pb-12 bg-background min-h-screen">
      {/* Header */}
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between py-10">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <LayoutDashboard className="h-8 w-8 text-accent-teal" aria-hidden="true" />
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
            <RefreshCcw className={loading ? "animate-spin h-4 w-4" : "h-4 w-4"} aria-hidden="true" />
            <AsyncLabel active={loading} idle="Refresh" loading="Refreshing" />
          </Button>
        </div>
      </header>

      {error ? (
        <div className="mb-6" role="alert">
          <ErrorCard message={error} />
        </div>
      ) : null}

      {data && (
        <div className="space-y-16">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
            {/* Main Insights Column */}
            <div className="lg:col-span-8 space-y-16">
              <section aria-label="Clinical Summary">
                <ClinicalSummary 
                  adherence={data.summary.adherence_score.value}
                  risk={data.summary.glycemic_risk.value}
                  nutrition={data.summary.nutrition_goal_score.value}
                  adherenceChart={data.charts.adherence.points}
                  riskChart={data.charts.glycemic_risk.points}
                  recommendation={data.insights.recommendations[0]}
                />
              </section>

              {/* Row 2: Metabolic Rhythms */}
              <section className="space-y-10">
                <div className="px-2">
                  <h2 className="text-h2 font-display text-foreground tracking-tight">Metabolic Rhythms</h2>
                  <p className="text-sm text-muted-foreground font-medium">Correlation of caloric intake and glycemic response stability</p>
                </div>
                
                <div className="space-y-12">
                  <CorrelationChart
                    calories={data.charts.calories.points}
                    risk={data.charts.glycemic_risk.points}
                  />

                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-10 px-1">
                    <NutritionBalanceChart chart={data.charts.macros} />
                    <MealClock bins={data.charts.meal_timing.bins} />
                  </div>
                </div>
              </section>

              {/* Row 3: Longitudinal Vitals */}
              <section className="space-y-10 pt-4">
                <div className="px-2 border-t border-border-soft pt-16">
                  <h2 className="text-h2 font-display text-foreground tracking-tight">Clinical Vitals</h2>
                  <p className="text-sm text-muted-foreground font-medium">Longitudinal baseline tracking for hemodynamic stability</p>
                </div>
                <div className="px-1">
                  <BloodPressureChart chart={data.charts.blood_pressure} />
                </div>
              </section>
            </div>

            {/* Sidebar: Alerts & Actions */}
            <aside className="lg:col-span-4 space-y-12 lg:sticky lg:top-8">
              <section 
                className="bg-panel border border-border-soft rounded-2xl p-8 shadow-sm"
                aria-labelledby="alerts-heading"
              >
                <div className="flex items-center justify-between mb-8 px-1">
                  <div className="space-y-1.5">
                    <h3 id="alerts-heading" className="text-lg font-semibold tracking-tight text-foreground">Active Alerts</h3>
                    <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-accent-teal">Clinical Priority</p>
                  </div>
                  <Badge className="bg-accent-teal/10 text-accent-teal border-accent-teal/20 h-6 px-2 rounded-lg flex items-center justify-center p-0 text-[11px] font-bold">
                    {data.alerts.length}
                  </Badge>
                </div>
                <div className="space-y-3">
                  {data.alerts.length ? (
                    data.alerts.slice(0, 4).map((alert) => (
                      <article
                        key={alert.id}
                        className="rounded-xl border border-border-soft bg-surface px-5 py-4 shadow-sm group hover:border-accent-teal/30 transition-all"
                      >
                        <div className="flex items-center justify-between gap-2 mb-1.5">
                          <span className="text-[13px] font-semibold text-foreground">
                            {alert.title}
                          </span>
                          <span
                            className={`text-[9px] font-bold uppercase tracking-widest ${
                              alert.severity === "critical"
                                ? "text-health-rose"
                                : alert.severity === "warning"
                                  ? "text-health-amber"
                                  : "text-health-teal"
                            }`}
                          >
                            {alert.severity}
                          </span>
                        </div>
                        <p className="text-[12px] text-muted-foreground leading-relaxed">
                          {alert.detail}
                        </p>
                      </article>
                    ))
                  ) : (
                    <div className="rounded-xl border border-dashed border-border-soft p-8 text-center text-[12px] text-muted-foreground bg-surface/50">
                      No critical alerts observed in this window.
                    </div>
                  )}
                </div>
              </section>

              <NextActions 
                recommendations={data.insights.recommendations}
                links={{
                  chat: "/chat",
                  meals: data.links.meals,
                  medications: data.links.medications
                }}
              />
            </aside>
          </div>
        </div>
      )}
    </main>
  );
}
