"use client";

import { CheckCircle2 } from "lucide-react";
import type { CarePlan } from "@/lib/types";

interface CarePlanCardProps {
  carePlan: CarePlan | undefined;
}

export function CarePlanCard({ carePlan }: CarePlanCardProps) {
  return (
    <div className="p-6 space-y-4 bg-[color:var(--panel-soft)]">
      <div className="flex items-center gap-2 mb-2">
        <div className="h-1.5 w-1.5 rounded-full bg-[color:var(--accent)]" />
        <span className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Clinical Decision</span>
      </div>
      
      <div className="space-y-3">
        {carePlan?.recommended_actions?.length ? (
          carePlan.recommended_actions.map((item: string, index: number) => (
            <div
              key={`${item}-${index}`}
              className="flex items-start gap-3 rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-3 shadow-sm transition-all hover:shadow-md"
            >
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[color:var(--accent)]" />
              <span className="text-sm font-bold text-[color:var(--foreground)] leading-snug">{item}</span>
            </div>
          ))
        ) : (
          <div className="py-8 text-center border border-dashed rounded-xl border-[color:var(--border-soft)] bg-[color:var(--surface)]">
            <p className="text-xs text-[color:var(--muted-foreground)] italic">Awaiting clinical orchestration...</p>
          </div>
        )}
      </div>

      {carePlan?.urgency && (
        <div className="flex items-center gap-2 pt-2">
          <div className={`h-1.5 w-1.5 rounded-full ${
            carePlan.urgency === "prompt" ? "bg-health-rose" : carePlan.urgency === "soon" ? "bg-health-amber" : "bg-health-teal"
          }`} />
          <span className="text-[9px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Urgency: {carePlan.urgency}</span>
        </div>
      )}
    </div>
  );
}
