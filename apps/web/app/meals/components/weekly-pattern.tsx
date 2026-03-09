"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getMealWeeklySummary } from "@/lib/api/meal-client";

function isoDate(value: Date): string {
  return value.toISOString().slice(0, 10);
}

function resolveWeekStart(today: Date): string {
  const normalized = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));
  const weekday = normalized.getUTCDay();
  const daysSinceMonday = (weekday + 6) % 7;
  normalized.setUTCDate(normalized.getUTCDate() - daysSinceMonday);
  return isoDate(normalized);
}

export function WeeklyPattern() {
  const initialWeekStart = resolveWeekStart(new Date());
  const [weekStart, setWeekStart] = useState(initialWeekStart);

  const { data: summary } = useQuery({
    queryKey: ["meal-weekly-summary", weekStart],
    queryFn: () => getMealWeeklySummary(weekStart),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Weekly Pattern Summary</CardTitle>
        <CardDescription>
          Seven-day rollup for meal volume, nutrition totals, and repetitive intake flags.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <label htmlFor="meal-week-start" className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">
            Weekly window start
          </label>
          <Input
            id="meal-week-start"
            type="date"
            value={weekStart}
            onChange={(event) => setWeekStart(event.target.value)}
            max={isoDate(new Date())}
          />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="metric-card">
            <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Meals logged</div>
            <div className="mt-1 text-sm font-medium">{summary?.meal_count ?? 0}</div>
          </div>
          <div className="metric-card">
            <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Total calories</div>
            <div className="mt-1 text-sm font-medium">{Math.round(summary?.totals.calories ?? 0)} kcal</div>
          </div>
        </div>
        <div className="space-y-2">
          <div className="text-sm font-semibold">Daily breakdown</div>
          {summary && Object.keys(summary.daily_breakdown).length > 0 ? (
            <div className="data-list">
              {Object.entries(summary.daily_breakdown)
                .sort(([left], [right]) => left.localeCompare(right))
                .map(([day, values]) => (
                  <div key={day} className="data-list-row sm:flex-row sm:items-center sm:justify-between">
                    <div className="text-sm font-medium">{day}</div>
                    <div className="app-muted text-xs">
                      {values.meal_count} meal(s) • {Math.round(values.calories)} kcal
                    </div>
                  </div>
                ))}
            </div>
          ) : (
            <p className="app-muted text-sm">No meals found in the selected weekly window.</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
