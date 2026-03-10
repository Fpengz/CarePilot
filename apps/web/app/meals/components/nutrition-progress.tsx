"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getMealDailySummary } from "@/lib/api/meal-client";

function isoDate(value: Date): string {
  return value.toISOString().slice(0, 10);
}

export function NutritionProgress() {
  const { data: summary } = useQuery({
    queryKey: ["meal-daily-summary"],
    queryFn: () => getMealDailySummary(isoDate(new Date())),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Today’s Nutrition Progress</CardTitle>
        <CardDescription>Consumed, remaining, and target values update as you log meals throughout the day.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="metric-card">
            <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Consumed calories</div>
            <div className="mt-1 text-sm font-medium">
              {Math.round(summary?.consumed.calories ?? 0)} / {Math.round(summary?.targets.calories ?? 0)} kcal
            </div>
          </div>
          <div className="metric-card">
            <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Remaining protein</div>
            <div className="mt-1 text-sm font-medium">{Math.round(summary?.remaining.protein_g ?? 0)} g</div>
          </div>
          <div className="metric-card">
            <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Remaining fiber</div>
            <div className="mt-1 text-sm font-medium">{Math.round(summary?.remaining.fiber_g ?? 0)} g</div>
          </div>
          <div className="metric-card">
            <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Remaining sodium</div>
            <div className="mt-1 text-sm font-medium">{Math.round(summary?.remaining.sodium_mg ?? 0)} mg</div>
          </div>
        </div>
        <div className="space-y-2">
          <div className="text-sm font-semibold">Possible gaps or imbalances</div>
          {summary?.insights.length ? (
            summary.insights.slice(0, 3).map((insight) => (
              <div
                key={insight.code}
                className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 dark:bg-[color:var(--panel-soft)]"
              >
                <div className="text-sm font-medium">{insight.title}</div>
                <p className="app-muted mt-1 text-xs">{insight.summary}</p>
              </div>
            ))
          ) : (
            <p className="app-muted text-sm">Log meals across a few days to unlock pattern-level guidance.</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
