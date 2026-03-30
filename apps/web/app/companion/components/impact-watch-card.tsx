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
    <div className="bg-panel border border-border-soft rounded-3xl overflow-hidden h-full flex flex-col shadow-sm">
      <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
        <div className="rounded-2xl border border-border-soft bg-surface p-5 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Target className="h-4 w-4 text-accent-teal" />
            <span className="text-micro-label font-bold uppercase tracking-widest text-accent-teal">Clinical Observation Window</span>
          </div>
          <div className="flex items-center justify-between text-sm font-semibold text-foreground">
            <span>{impact?.baseline_window ?? "Baseline"}</span>
            <span className="text-muted-foreground opacity-40">→</span>
            <span>{impact?.comparison_window ?? "Follow-up"}</span>
          </div>
        </div>

        <div className="space-y-3">
          {deltaEntries.length ? (
            deltaEntries.map(([key, value]) => {
              const val = value as number;
              const isPositive = val > 0;
              const isZero = val === 0;
              const label = METRIC_LABELS[key] || key.replace(/_/g, " ");

              return (
                <div key={key} className="flex items-center justify-between rounded-2xl border border-border-soft bg-surface p-5 shadow-sm transition-all hover:bg-surface/80 group">
                  <div className="flex flex-col">
                    <span className="text-sm font-semibold text-foreground leading-none group-hover:text-accent-teal transition-colors">{label}</span>
                    <span className="text-micro-label text-muted-foreground uppercase tracking-tighter mt-2">Gap vs Clinical Target</span>
                  </div>
                  <div
                    className={`flex items-center gap-2 font-mono text-base font-bold ${
                      isZero ? "text-muted-foreground" : isPositive ? "text-emerald-600" : "text-rose-600"
                    }`}
                  >
                    {isZero ? <Minus className="h-4 w-4 opacity-40" /> : isPositive ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />}
                    {val.toFixed(2)}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="flex flex-col items-center justify-center py-16 text-center bg-surface/50 rounded-2xl border border-dashed border-border-soft">
               <div className="h-12 w-12 rounded-2xl bg-panel border border-border-soft flex items-center justify-center mb-3">
                  <Minus className="h-6 w-6 text-muted-foreground opacity-20" />
               </div>
               <p className="text-sm text-muted-foreground italic">No longitudinal deltas projected.</p>
            </div>
          )}
        </div>
      </div>

      {impact?.interventions_measured && impact.interventions_measured.length > 0 && (
        <div className="px-6 py-4 border-t border-border-soft bg-panel/50 shrink-0">
          <span className="text-micro-label font-bold text-muted-foreground uppercase tracking-widest truncate block">
            Measured: {impact.interventions_measured.join(", ")}
          </span>
        </div>
      )}
    </div>
  );
}
