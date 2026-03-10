"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { listMealRecords } from "@/lib/api/meal-client";

export function MealRecordsList() {
  const { data: recordsResult } = useQuery({
    queryKey: ["meal-records"],
    queryFn: () => listMealRecords(),
  });

  const recordItems = (recordsResult as { records?: Array<Record<string, unknown>> } | null)?.records ?? [];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Saved Meal Records</CardTitle>
        <CardDescription>Recent persisted meals from the read endpoint.</CardDescription>
      </CardHeader>
      <CardContent>
        {recordItems.length > 0 ? (
          <div className="max-h-[32rem] overflow-y-auto pr-1">
            <div className="data-list">
              {recordItems.map((record, index) => (
                <div
                  key={String(record.id ?? record.meal_name ?? index)}
                  className="data-list-row sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <div className="text-sm font-medium">{String(record.meal_name ?? "Meal record")}</div>
                    <div className="app-muted mt-1 text-xs">
                      {String(record.captured_at ?? record.created_at ?? "Unknown capture time")}
                    </div>
                  </div>
                  <div className="text-sm font-medium">
                    {typeof record.calories_estimate === "number"
                      ? `${Math.round(record.calories_estimate)} kcal`
                      : typeof record.estimated_calories === "number"
                        ? `${Math.round(Number(record.estimated_calories))} kcal`
                        : "—"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="app-muted text-sm">Load meal records to preview saved items.</p>
        )}
      </CardContent>
    </Card>
  );
}
