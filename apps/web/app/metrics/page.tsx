"use client";

import { useEffect, useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { JsonViewer } from "@/components/app/json-viewer";
import { PageTitle } from "@/components/app/page-title";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { listMetricTrends } from "@/lib/api/meal-client";
import type { MetricTrendApi } from "@/lib/types";

const METRIC_OPTIONS = ["meal:calories", "adherence:rate", "biomarker:ldl", "biomarker:hba1c"] as const;

export default function MetricsPage() {
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(["meal:calories", "adherence:rate", "biomarker:ldl"]);
  const [items, setItems] = useState<MetricTrendApi[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function refreshTrends(metrics: string[]) {
    const response = await listMetricTrends(metrics);
    setItems(response.items);
  }

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        const response = await listMetricTrends(selectedMetrics);
        if (cancelled) return;
        setItems(response.items);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [selectedMetrics]);

  return (
    <div>
      <PageTitle
        eyebrow="Metrics"
        title="Numerical Trend Analysis"
        description="Inspect deterministic deltas and trend directions for nutrition, adherence, and biomarker metrics."
        tags={["delta", "percent change", "trend direction"]}
      />

      <div className="page-grid">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Trend Filters</CardTitle>
            <CardDescription>Select metrics and refresh deterministic trend computations from persisted records.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {METRIC_OPTIONS.map((metric) => {
                const active = selectedMetrics.includes(metric);
                return (
                  <Button
                    key={metric}
                    variant={active ? "default" : "secondary"}
                    aria-pressed={active}
                    onClick={() => {
                      setSelectedMetrics((current) =>
                        current.includes(metric)
                          ? current.filter((item) => item !== metric)
                          : [...current, metric],
                      );
                    }}
                  >
                    {metric}
                  </Button>
                );
              })}
            </div>
            <Button
              disabled={loading}
              onClick={async () => {
                setError(null);
                setLoading(true);
                try {
                  await refreshTrends(selectedMetrics);
                } catch (e) {
                  setError(e instanceof Error ? e.message : String(e));
                } finally {
                  setLoading(false);
                }
              }}
            >
              <AsyncLabel active={loading} idle="Refresh Trends" loading="Refreshing" />
            </Button>
          </CardContent>
        </Card>

        <div className="stack-grid">
          {error ? <ErrorCard message={error} /> : null}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Trend Overview</CardTitle>
              <CardDescription>Direction, delta, and slope for each selected metric.</CardDescription>
            </CardHeader>
            <CardContent>
              {items.length > 0 ? (
                <div className="grid gap-3 md:grid-cols-2">
                  {items.map((item) => (
                    <div key={item.metric} className="metric-card">
                      <div className="flex items-center justify-between gap-2">
                        <div className="text-sm font-semibold">{item.metric}</div>
                        <Badge variant={item.direction === "increase" ? "default" : "outline"}>{item.direction}</Badge>
                      </div>
                      <div className="app-muted mt-2 text-xs">Points: {item.points.length}</div>
                      <div className="mt-1 text-sm">Delta: {item.delta.toFixed(4)}</div>
                      <div className="text-sm">Slope / point: {item.slope_per_point.toFixed(4)}</div>
                      <div className="text-sm">
                        Percent change: {item.percent_change == null ? "n/a" : `${item.percent_change.toFixed(2)}%`}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="app-muted text-sm">No trend data for the selected metrics yet.</p>
              )}
            </CardContent>
          </Card>
          <JsonViewer
            title="Raw Trend Payload"
            description="Detailed time-series points for each selected metric."
            data={{ items }}
            emptyLabel="No trend payload loaded."
          />
        </div>
      </div>
    </div>
  );
}
