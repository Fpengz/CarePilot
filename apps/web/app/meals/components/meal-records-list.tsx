"use client";

import { useQuery } from "@tanstack/react-query";
import { listMealRecords } from "@/lib/api/meal-client";

export function MealRecordsList() {
  const { data: recordsResult } = useQuery({
    queryKey: ["meal-records"],
    queryFn: () => listMealRecords(),
  });

  const recordItems = (recordsResult as { records?: Array<Record<string, unknown>> } | null)?.records ?? [];

  return (
    <div className="glass-card">
      <div className="mb-6">
        <h3 className="text-base font-bold">Meal History Timeline</h3>
        <p className="text-xs text-[color:var(--muted-foreground)]">Most recent meal logs and estimated calories.</p>
      </div>
      <div className="space-y-4">
        {recordItems.length > 0 ? (
          <div className="max-h-[32rem] overflow-y-auto pr-1 scrollbar-hide">
            <div className="space-y-3">
              {recordItems.map((record, index) => (
                <div
                  key={String(record.id ?? `${record.meal_name ?? 'unknown'}${index}`)}
                  className="rounded-xl border border-white/10 bg-white/10 dark:bg-black/10 px-4 py-3 transition-colors hover:bg-white/20 dark:hover:bg-black/20"
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0">
                      <div className="truncate text-sm font-bold">{String(record.meal_name ?? "Meal record")}</div>
                      <div className="mt-1 text-[10px] font-medium text-[color:var(--muted-foreground)] opacity-60">
                        {String(record.captured_at ?? record.created_at ?? "Unknown capture time")}
                      </div>
                    </div>
                    <div className="text-sm font-bold text-health-teal">
                      {typeof record.calories_estimate === "number"
                        ? `${Math.round(record.calories_estimate)} kcal`
                        : typeof record.estimated_calories === "number"
                          ? `${Math.round(Number(record.estimated_calories))} kcal`
                          : "—"}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="py-12 text-center">
            <p className="text-xs text-[color:var(--muted-foreground)] opacity-60">No meal history yet. Log a meal to build the timeline.</p>
          </div>
        )}
      </div>
    </div>
  );
}
