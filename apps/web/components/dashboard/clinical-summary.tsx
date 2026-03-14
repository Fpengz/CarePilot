"use client";

import { Sparkles, Activity, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface ClinicalSummaryProps {
  adherence: number;
  risk: number;
  nutrition: number;
  recommendation: string;
}

export function ClinicalSummary({
  adherence,
  risk,
  nutrition,
  recommendation,
}: ClinicalSummaryProps) {
  return (
    <div className="clinical-panel relative overflow-hidden">
      <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
        <Sparkles className="h-24 w-24" />
      </div>
      
      <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
        <div className="max-w-2xl space-y-4">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[color:var(--accent)]/10 text-[color:var(--accent)]">
              <Activity className="h-3.5 w-3.5" />
            </span>
            <span className="clinical-kicker">Companion Digest</span>
          </div>
          
          <h3 className="clinical-title">
            Your health signals remain <span className="text-[color:var(--accent)]">stable</span> this week.
          </h3>
          
          <p className="clinical-body max-w-xl">
            Based on your recent meal logs and medication adherence, your metabolic load is balanced. 
            However, we noticed a slight increase in glycemic risk following late-evening meals.
          </p>

          <div className="flex flex-wrap gap-4 pt-2">
            <div className="flex items-center gap-2 rounded-full border border-[color:var(--border-soft)] bg-[color:var(--surface)] px-4 py-2">
              <div className={cn("h-2 w-2 rounded-full", adherence > 80 ? "bg-emerald-500" : "bg-amber-500")} />
              <span className="text-[11px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)]">
                Adherence: {adherence}%
              </span>
            </div>
            <div className="flex items-center gap-2 rounded-full border border-[color:var(--border-soft)] bg-[color:var(--surface)] px-4 py-2">
              <div className={cn("h-2 w-2 rounded-full", risk < 30 ? "bg-emerald-500" : "bg-rose-500")} />
              <span className="text-[11px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)]">
                Risk: {risk}/100
              </span>
            </div>
          </div>
        </div>

        <div className="w-full md:w-80">
          <div className="rounded-2xl bg-[color:var(--accent)]/5 p-6 border border-[color:var(--accent)]/10">
            <div className="mb-3 flex items-center gap-2 text-[color:var(--accent)]">
              <AlertCircle className="h-4 w-4" />
              <span className="text-[11px] font-bold uppercase tracking-widest">Action Required</span>
            </div>
            <p className="text-sm font-medium leading-relaxed text-[color:var(--foreground)]">
              "{recommendation}"
            </p>
            <button className="mt-4 text-[11px] font-bold uppercase tracking-wider text-[color:var(--accent)] hover:underline">
              Implement recommendation →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
