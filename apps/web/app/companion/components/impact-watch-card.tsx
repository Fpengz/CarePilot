"use client";

import { ArrowUp, ArrowDown, Minus, Target } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { ImpactSummary } from "@/lib/types";

interface ImpactWatchCardProps {
  impact: ImpactSummary | undefined;
}

const METRIC_LABELS: Record<string, string> = {
  meal_risk_streak_vs_target: "Meal Risk Streak",
  reminder_response_rate_vs_target: "Reminder Response",
  symptom_severity_vs_target: "Symptom Severity",
  adherence_rate_vs_target: "Adherence Rate",
};

export function ImpactWatchCard({ impact }: ImpactWatchCardProps) {
  const deltaEntries = Object.entries(impact?.deltas ?? {});

  return (
    <Card className="p-0 overflow-hidden">
      <CardContent className="p-0 h-full flex flex-col">
      <div className="flex-1 overflow-y-auto p-5 space-y-5 custom-scrollbar">
        <div className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--panel-soft)] p-4">
          <div className="flex items-center gap-2 mb-3">
            <Target className="h-3.5 w-3.5 text-[color:var(--accent)]" />
            <span className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--accent)]">Observation Window</span>
          </div>
          <div className="flex items-center justify-between text-[11px] font-bold text-[color:var(--foreground)]">
            <span>{impact?.baseline_window ?? "Baseline"}</span>
            <span className="text-[color:var(--muted-foreground)]">→</span>
            <span>{impact?.comparison_window ?? "Follow-up"}</span>
          </div>
        </div>

        <div className="space-y-2">
          {deltaEntries.length ? (
            deltaEntries.map(([key, value]) => {
              const val = value as number;
              const isPositive = val > 0;
              const isZero = val === 0;
              const label = METRIC_LABELS[key] || key.replace(/_/g, " ");

              return (
                <div key={key} className="flex items-center justify-between rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-4 shadow-sm transition-all hover:shadow-md">
                  <div className="flex flex-col">
                    <span className="text-xs font-bold text-[color:var(--foreground)] leading-none">{label}</span>
                    <span className="text-[9px] text-[color:var(--muted-foreground)] font-bold uppercase tracking-tighter mt-1.5">Gap vs Target</span>
                  </div>
                  <div
                    className={`flex items-center gap-1.5 font-mono text-sm font-bold ${
                      isZero ? "text-[color:var(--muted-foreground)]" : isPositive ? "text-health-teal" : "text-health-rose"
                    }`}
                  >
                    {isZero ? <Minus className="h-3 w-3" /> : isPositive ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />}
                    {val.toFixed(2)}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
               <div className="h-10 w-10 rounded-full bg-[color:var(--panel-soft)] flex items-center justify-center mb-2">
                  <Minus className="h-5 w-5 text-[color:var(--muted-foreground)]/40" />
               </div>
               <p className="text-xs text-[color:var(--muted-foreground)] italic">No longitudinal deltas projected.</p>
            </div>
          )}
        </div>
      </div>

      {impact?.interventions_measured && impact.interventions_measured.length > 0 && (
        <div className="px-5 py-3 border-t border-[color:var(--border-soft)] bg-[color:var(--panel-soft)] shrink-0">
          <span className="text-[9px] font-bold text-[color:var(--muted-foreground)] uppercase tracking-widest truncate block">
            Scope: {impact.interventions_measured.join(", ")}
          </span>
        </div>
      )}
      </CardContent>
    </Card>
  );
}
