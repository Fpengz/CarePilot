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
          
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-8">
              <ClinicalSummary 
                adherence={data.summary.adherence_score.value}
                risk={data.summary.glycemic_risk.value}
                nutrition={data.summary.nutrition_goal_score.value}
                recommendation={data.insights.recommendations[0]}
              />
              <NutritionBalanceChart 
                chart={data.charts.macros} 
              />
            </div>
            
            <div className="space-y-8">
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
        </div>
      )}
    </div>
  );
}
