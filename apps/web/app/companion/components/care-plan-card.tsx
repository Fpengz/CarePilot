"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { CarePlan } from "@/lib/types";

interface CarePlanCardProps {
  carePlan: CarePlan | undefined;
}

export function CarePlanCard({ carePlan }: CarePlanCardProps) {
  return (
    <div className="section-stack">
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
                className="clinical-alert text-sm"
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
          <div className="clinical-alert">
            {carePlan?.why_now ?? "No why-now rationale yet."}
          </div>
          <div className="clinical-alert">
            {carePlan?.reasoning_summary ?? "No reasoning summary yet."}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
