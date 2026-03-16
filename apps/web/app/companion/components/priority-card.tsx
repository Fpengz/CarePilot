"use client";

import type { CarePlan } from "@/lib/types";

interface PriorityCardProps {
  carePlan: CarePlan | undefined;
}

export function PriorityCard({ carePlan }: PriorityCardProps) {
  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <div className="h-1.5 w-1.5 rounded-full bg-health-teal" />
        <span className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Assessment</span>
      </div>
      <div>
        <h3 className="text-lg font-bold tracking-tight text-[color:var(--foreground)] leading-tight">
          {carePlan?.headline ?? "Establishing priority state…"}
        </h3>
        <p className="mt-2 text-sm leading-relaxed text-[color:var(--muted-foreground)] font-medium">
          {carePlan?.summary ?? "Synthesizing current patient signals and history."}
        </p>
      </div>
      {carePlan?.policy_status && (
        <div className="pt-2">
          <span className="text-[9px] font-bold text-[color:var(--muted-foreground)] uppercase tracking-widest bg-[color:var(--panel-soft)] px-2 py-1 rounded border border-[color:var(--border-soft)]">
            Policy Decision: {carePlan.policy_status}
          </span>
        </div>
      )}
    </div>
  );
}
