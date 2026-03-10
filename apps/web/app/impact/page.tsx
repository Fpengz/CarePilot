"use client";

import { useEffect, useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getImpactSummary } from "@/lib/api/companion-client";
import type { ImpactSummaryApi } from "@/lib/types";

export default function ImpactPage() {
  const [summary, setSummary] = useState<ImpactSummaryApi | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function refresh() {
    const response = await getImpactSummary();
    setSummary(response.summary);
  }

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        const response = await getImpactSummary();
        if (!cancelled) setSummary(response.summary);
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
  }, []);

  const deltaEntries = Object.entries(summary?.deltas ?? {});
  const metricEntries = Object.entries(summary?.tracked_metrics ?? {});

  return (
    <div>
      <PageTitle
        eyebrow="Impact"
        title="Impact Summary"
        description="Track the baseline, the next follow-up window, and the intervention metrics that show whether the companion is actually helping."
        tags={["outcomes", "baseline", "follow-up"]}
      />

      <div className="page-grid">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Follow-Up Windows</CardTitle>
            <CardDescription>Calls `GET /api/v1/impact/summary` and frames the current state as a baseline plus the next measurement window.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2">
              <Button
                disabled={loading}
                onClick={async () => {
                  setError(null);
                  setLoading(true);
                  try {
                    await refresh();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoading(false);
                  }
                }}
              >
                <AsyncLabel active={loading} idle="Refresh Impact" loading="Refreshing" />
              </Button>
              {summary ? <Badge variant="outline">Opportunities: {summary.intervention_opportunities}</Badge> : null}
            </div>

            <div className="rounded-xl border border-[color:var(--border)] bg-white/70 p-4 dark:bg-[color:var(--panel-soft)]">
              <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Baseline Window</div>
              <div className="mt-1 text-lg font-semibold">{summary?.baseline_window ?? "Loading baseline…"}</div>
              <p className="app-muted mt-2 text-sm">Next comparison: {summary?.comparison_window ?? "No follow-up window yet."}</p>
            </div>
          </CardContent>
        </Card>

        <div className="stack-grid">
          {error ? <ErrorCard message={error} /> : null}

          <Card>
            <CardHeader>
              <CardTitle>Interventions Measured</CardTitle>
              <CardDescription>These are the actions the companion expects to influence near-term outcomes.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {summary?.interventions_measured?.length ? (
                summary.interventions_measured.map((item) => (
                  <div key={item} className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 text-sm dark:bg-[color:var(--panel-soft)]">
                    {item}
                  </div>
                ))
              ) : (
                <p className="app-muted text-sm">No measured interventions yet.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Impact Deltas</CardTitle>
              <CardDescription>Negative values indicate larger gaps to close; positive values indicate stronger current performance.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-2">
              {deltaEntries.length ? (
                deltaEntries.map(([key, value]) => (
                  <div key={key} className="metric-card">
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">{key}</div>
                    <div className="mt-2 text-xl font-semibold">{value.toFixed(2)}</div>
                  </div>
                ))
              ) : (
                <p className="app-muted text-sm">No delta view available yet.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Current Metrics</CardTitle>
              <CardDescription>These tracked metrics define the current baseline the follow-up window should improve.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-2">
              {metricEntries.length ? (
                metricEntries.map(([key, value]) => (
                  <div key={key} className="metric-card">
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">{key}</div>
                    <div className="mt-2 text-xl font-semibold">{value}</div>
                  </div>
                ))
              ) : (
                <p className="app-muted text-sm">Loading metrics…</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Improvement Signals</CardTitle>
              <CardDescription>Positive signals that indicate the current baseline is already moving in the right direction.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {summary?.improvement_signals?.length ? (
                summary.improvement_signals.map((item) => (
                  <div key={item} className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 text-sm dark:bg-[color:var(--panel-soft)]">
                    {item}
                  </div>
                ))
              ) : (
                <p className="app-muted text-sm">No improvement signals available yet.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
