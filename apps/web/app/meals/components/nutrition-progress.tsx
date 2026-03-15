"use client";

import { useQuery } from "@tanstack/react-query";
import { getMealDailySummary } from "@/lib/api/meal-client";
import { cn } from "@/lib/utils";

function isoDate(value: Date): string {
  return value.toISOString().slice(0, 10);
}

export function NutritionProgress() {
  const { data: summary } = useQuery({
    queryKey: ["meal-daily-summary"],
    queryFn: () => getMealDailySummary(isoDate(new Date())),
  });

  return (
    <div className="glass-card">
      <div className="mb-6">
        <h3 className="text-base font-bold">Today’s Nutrition Progress</h3>
        <p className="text-xs text-[color:var(--muted-foreground)]">Consumed, remaining, and target values update as you log meals.</p>
      </div>
      <div className="space-y-6">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-white/10 bg-white/10 dark:bg-black/10 p-3">
            <div className="text-[9px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Consumed calories</div>
            <div className="mt-1 text-sm font-bold">
              {Math.round(summary?.consumed.calories ?? 0)} <span className="text-[10px] font-medium opacity-60">/ {Math.round(summary?.targets.calories ?? 0)} kcal</span>
            </div>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/10 dark:bg-black/10 p-3">
            <div className="text-[9px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Remaining protein</div>
            <div className="mt-1 text-sm font-bold">{Math.round(summary?.remaining.protein_g ?? 0)} <span className="text-[10px] font-medium opacity-60">g</span></div>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/10 dark:bg-black/10 p-3">
            <div className="text-[9px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Remaining fiber</div>
            <div className="mt-1 text-sm font-bold">{Math.round(summary?.remaining.fiber_g ?? 0)} <span className="text-[10px] font-medium opacity-60">g</span></div>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/10 dark:bg-black/10 p-3">
            <div className="text-[9px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Remaining sodium</div>
            <div className="mt-1 text-sm font-bold">{Math.round(summary?.remaining.sodium_mg ?? 0)} <span className="text-[10px] font-medium opacity-60">mg</span></div>
          </div>
        </div>
        <div className="space-y-3">
          <div className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Possible gaps or imbalances</div>
          {summary?.insights.length ? (
            <div className="grid gap-2">
              {summary.insights.slice(0, 3).map((insight) => (
                <div
                  key={insight.code}
                  className="rounded-xl bg-health-amber-soft border border-health-amber/10 p-3"
                >
                  <div className="text-xs font-bold text-health-amber">{insight.title}</div>
                  <p className="mt-1 text-[11px] leading-relaxed opacity-80">{insight.summary}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="py-4 text-center text-xs text-[color:var(--muted-foreground)] opacity-60">Log meals across a few days to unlock pattern-level guidance.</p>
          )}
        </div>
      </div>
    </div>
  );
}
