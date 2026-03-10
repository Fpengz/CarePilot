"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ImpactSummary } from "@/lib/types";

interface ImpactWatchCardProps {
  impact: ImpactSummary | undefined;
}

export function ImpactWatchCard({ impact }: ImpactWatchCardProps) {
  const deltaEntries = Object.entries(impact?.deltas ?? {});

  return (
    <Card>
      <CardHeader>
        <CardTitle>Impact to Watch</CardTitle>
        <CardDescription>
          Track which metric gaps should improve if the patient follows through on this plan.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 dark:bg-[color:var(--panel-soft)]">
          <div className="font-medium">
            {`${impact?.baseline_window ?? "No baseline window yet"} -> ${impact?.comparison_window ?? "No follow-up window yet"}`}
          </div>
          <p className="app-muted mt-2">
            {impact?.interventions_measured?.join(", ") ?? "No measured interventions yet."}
          </p>
        </div>
        {deltaEntries.length ? (
          <div className="grid gap-3 md:grid-cols-2">
            {deltaEntries.map(([key, value]) => (
              <div key={key} className="metric-card">
                <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">{key}</div>
                <div className="mt-2 text-xl font-semibold">{(value as number).toFixed(2)}</div>
              </div>
            ))}
          </div>
        ) : (
          <p className="app-muted text-sm">No impact deltas yet.</p>
        )}
      </CardContent>
    </Card>
  );
}
