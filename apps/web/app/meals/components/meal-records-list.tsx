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
    <div className="space-y-6">
      <div className="px-1">
        <h3 className="text-lg font-semibold tracking-tight text-foreground">Meal History Timeline</h3>
        <p className="text-[13px] text-muted-foreground leading-relaxed">Most recent meal logs and estimated calories.</p>
      </div>
      <div className="space-y-4">
        {recordItems.length > 0 ? (
          <div className="space-y-8">
            {orderedDates.map((dateKey) => (
              <section key={dateKey} className="space-y-4">
                <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-accent-teal px-1">
                  {dateKey}
                </h4>
                <div className="grid gap-3">
                  {groupedRecords[dateKey].map((record, index) => (
                    <article
                      key={String(record.id ?? `${record.meal_name ?? "unknown"}${index}`)}
                      className="rounded-xl border border-border-soft bg-panel px-5 py-4 transition-all hover:border-accent-teal/30 shadow-sm group"
                    >
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                        <div className="min-w-0">
                          <div className="truncate text-[13px] font-bold text-foreground">{String(record.meal_name ?? "Meal record")}</div>
                          <div className="mt-1 text-[11px] font-medium text-muted-foreground">
                            {record.captured_at || record.created_at
                              ? formatDateTime((record.captured_at ?? record.created_at!) as string)
                              : "Unknown capture time"}
                          </div>
                        </div>
                        <div className="text-[13px] font-bold text-health-teal bg-health-teal/5 px-2.5 py-1 rounded-lg border border-health-teal/10">
                          {typeof record.calories_estimate === "number"
                            ? `${Math.round(record.calories_estimate)} kcal`
                            : typeof record.estimated_calories === "number"
                              ? `${Math.round(Number(record.estimated_calories))} kcal`
                              : "—"}
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            ))}
          </div>
        ) : (
          <div className="py-16 text-center bg-panel border border-dashed border-border-soft rounded-2xl">
            <p className="text-[13px] text-muted-foreground font-medium italic opacity-60">
              No meal history observed in this window.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
