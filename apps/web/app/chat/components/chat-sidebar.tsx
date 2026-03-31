"use client";

import { Activity, Bell, Utensils } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { getDashboardOverview } from "@/lib/api/dashboard-client";
import { listUpcomingReminderOccurrences } from "@/lib/api/reminder-client";
import { cn } from "@/lib/utils";

export function ChatSidebar() {
  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ["dashboard-overview"],
    queryFn: () => getDashboardOverview({ range: "7d" }),
  });

  const { data: reminders, isLoading: remindersLoading } = useQuery({
    queryKey: ["upcoming-reminders"],
    queryFn: listUpcomingReminderOccurrences,
  });

  const adherence = overview?.summary.adherence_score.value ?? 0;
  const upcomingCount = reminders?.items.length ?? 0;

  return (
    <div className="space-y-10 py-2">
      <section className="space-y-6">
        <div className="space-y-1.5 px-1">
          <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-accent-teal">Clinical Context</h4>
          <p className="text-[13px] text-muted-foreground leading-relaxed">
            Real-time health signals guiding this conversation.
          </p>
        </div>

        <div className="space-y-8 pt-2">
          <div className="group transition-opacity hover:opacity-80">
            <div className="flex items-baseline justify-between mb-1">
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Adherence (7d)</span>
              <span className="text-xl font-display font-semibold text-foreground">
                {overviewLoading ? "..." : `${Math.round(adherence)}%`}
              </span>
            </div>
            <div className="h-1 w-full bg-panel rounded-full overflow-hidden">
              <div 
                className="h-full bg-accent-teal transition-all duration-1000" 
                style={{ width: `${adherence}%` }}
              />
            </div>
          </div>

          <div className="flex items-baseline justify-between group transition-opacity hover:opacity-80">
            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Reminders Today</span>
            <span className="text-lg font-semibold text-foreground">
              {remindersLoading ? "..." : `${upcomingCount} active`}
            </span>
          </div>

          <div className="flex items-baseline justify-between group transition-opacity hover:opacity-80 border-t border-border-soft/50 pt-6">
            <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">Metabolic Goal</span>
            <span className="text-lg font-semibold text-foreground">
              {overviewLoading ? "..." : `${overview?.summary.nutrition_goal_score.value ?? 0}/100`}
            </span>
          </div>
        </div>
      </section>

      <div className="h-px bg-border-soft/30 mx-1" aria-hidden="true" />

      <section className="space-y-4 px-1">
        <h5 className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground/60">
          Active Care Priorities
        </h5>
        <ul className="space-y-4">
          {overview?.insights.recommendations.slice(0, 2).map((rec, i) => (
            <li key={i} className="group flex items-start gap-3">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-accent-teal/40 group-hover:bg-accent-teal transition-colors" />
              <p className="text-[13px] leading-relaxed text-muted-foreground group-hover:text-foreground transition-colors">
                {rec}
              </p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
