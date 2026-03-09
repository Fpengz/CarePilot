"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getDailySuggestions } from "@/lib/api/recommendation-client";

export function DailyMealSuggestions() {
  const { data: response, isLoading } = useQuery({
    queryKey: ["daily-meal-suggestions"],
    queryFn: getDailySuggestions,
  });

  const suggestions = response?.bundle.suggestions ?? {};
  const slots = ["breakfast", "lunch", "dinner", "snack"];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Daily Meal Suggestions</CardTitle>
        <CardDescription>
          AI-generated suggestions based on your health profile and recent meal history.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <p className="app-muted text-sm text-center py-4">Generating personalized suggestions...</p>
        ) : Object.keys(suggestions).length === 0 ? (
          <p className="app-muted text-sm text-center py-4">No suggestions available for today yet.</p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {slots.map((slot) => {
              const item = suggestions[slot];
              if (!item) return null;
              return (
                <div
                  key={slot}
                  className="rounded-xl border border-[color:var(--border)] bg-white/60 p-4 dark:bg-[color:var(--panel-soft)]"
                >
                  <div className="flex items-center justify-between gap-2">
                    <Badge variant="outline" className="capitalize">
                      {slot}
                    </Badge>
                    <Badge variant="outline">{Math.round(item.confidence * 100)}% Match</Badge>
                  </div>
                  <div className="mt-2 font-semibold">{item.title}</div>
                  <div className="text-xs text-[color:var(--muted-foreground)] mb-2">{item.venue_type}</div>
                  <ul className="space-y-1">
                    {item.why_it_fits.map((reason, idx) => (
                      <li key={idx} className="text-xs flex gap-2">
                        <span className="text-[color:var(--accent)]">•</span>
                        <span>{reason}</span>
                      </li>
                    ))}
                  </ul>
                  {item.caution_notes.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-[color:var(--border)]">
                      <div className="text-[10px] uppercase font-bold text-amber-600 dark:text-amber-400">Cautions</div>
                      {item.caution_notes.map((note, idx) => (
                        <p key={idx} className="text-[10px] text-amber-700 dark:text-amber-300">
                          {note}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
