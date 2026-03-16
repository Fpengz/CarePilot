"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { listMealRecords } from "@/lib/api/meal-client";
import { formatDate, formatDateTime } from "@/lib/time";

export function MealRecordsList() {
  const { data: recordsResult } = useQuery({
    queryKey: ["meal-records"],
    queryFn: () => listMealRecords(),
  });

  const recordItems = useMemo(
    () => (recordsResult as { records?: Array<Record<string, unknown>> } | null)?.records ?? [],
    [recordsResult]
  );
  const groupedRecords = useMemo(() => {
    const grouped: Record<string, Array<Record<string, unknown>>> = {};
    for (const record of recordItems) {
      const rawDate = (record.captured_at ?? record.created_at) as string;
      const key = rawDate ? formatDate(rawDate) : "Unknown date";
      if (!grouped[key]) grouped[key] = [];
      grouped[key].push(record);
    }
    return grouped;
  }, [recordItems]);
  const orderedDates = useMemo(() => Object.keys(groupedRecords), [groupedRecords]);

  return (
    <div className="glass-card">
      <div className="mb-6">
        <h3 className="text-base font-bold">Meal History Timeline</h3>
        <p className="text-xs text-[color:var(--muted-foreground)]">Most recent meal logs and estimated calories.</p>
      </div>
      <div className="space-y-4">
        {recordItems.length > 0 ? (
          <div className="max-h-[32rem] overflow-y-auto pr-1 scrollbar-hide">
            <div className="space-y-5">
              {orderedDates.map((dateKey) => (
                <div key={dateKey} className="space-y-3">
                  <div className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">
                    {dateKey}
                  </div>
                  <div className="space-y-3">
                    {groupedRecords[dateKey].map((record, index) => (
                      <div
                        key={String(record.id ?? `${record.meal_name ?? "unknown"}${index}`)}
                        className="rounded-xl border border-white/10 bg-white/10 dark:bg-black/10 px-4 py-3 transition-colors hover:bg-white/20 dark:hover:bg-black/20"
                      >
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                          <div className="min-w-0">
                            <div className="truncate text-sm font-bold">{String(record.meal_name ?? "Meal record")}</div>
                            <div className="mt-1 text-[10px] font-medium text-[color:var(--muted-foreground)] opacity-60">
                              {record.captured_at || record.created_at
                                ? formatDateTime((record.captured_at ?? record.created_at!) as string)
                                : "Unknown capture time"}
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
              ))}
            </div>
          </div>
        ) : (
          <div className="py-12 text-center">
            <p className="text-xs text-[color:var(--muted-foreground)] opacity-60">
              No meal history yet. Log a meal to build the timeline.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
