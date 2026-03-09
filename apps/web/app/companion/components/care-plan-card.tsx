"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { CarePlan } from "@/lib/types";

interface CarePlanCardProps {
  carePlan: CarePlan | undefined;
}

export function CarePlanCard({ carePlan }: CarePlanCardProps) {
  return (
    <div className="stack-grid">
      <Card>
        <CardHeader>
          <CardTitle>Recommended Next Step</CardTitle>
          <CardDescription>
            The companion turns the current state and message intent into a bounded plan.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {carePlan?.recommended_actions?.length ? (
            carePlan.recommended_actions.map((item: string) => (
              <div
                key={item}
                className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 text-sm dark:bg-[color:var(--panel-soft)]"
              >
                {item}
              </div>
            ))
          ) : (
            <p className="app-muted text-sm">No companion actions yet.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Why This Matters</CardTitle>
          <CardDescription>
            Reasoning and timing signals explain why the companion chose this intervention now.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 dark:bg-[color:var(--panel-soft)]">
            {carePlan?.why_now ?? "No why-now rationale yet."}
          </div>
          <div className="rounded-xl border border-[color:var(--border)] bg-white/60 p-3 dark:bg-[color:var(--panel-soft)]">
            {carePlan?.reasoning_summary ?? "No reasoning summary yet."}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
