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
    <aside className="hidden w-80 space-y-6 lg:block">
      <div className="clinical-card space-y-6">
        <div className="space-y-1">
          <h4 className="clinical-subtitle">Clinical Context</h4>
          <p className="text-xs text-[color:var(--muted-foreground)]">
            Real-time health signals guiding this conversation.
          </p>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)] opacity-70">
                Adherence (7d)
              </div>
              <div className="text-sm font-semibold">{overviewLoading ? "..." : `${adherence}%`}</div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/10 text-amber-600">
              <Bell className="h-5 w-5" />
            </div>
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)] opacity-70">
                Reminders Today
              </div>
              <div className="text-sm font-semibold">{remindersLoading ? "..." : upcomingCount} active</div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10 text-blue-600">
              <Utensils className="h-5 w-5" />
            </div>
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)] opacity-70">
                Latest Signal
              </div>
              <div className="text-sm font-semibold truncate max-w-[120px]">
                {overview?.summary.nutrition_goal_score.value ?? 0}/100 Goal
              </div>
            </div>
          </div>
        </div>

        <div className="clinical-divider" />

        <div className="space-y-3">
          <div className="text-[10px] font-bold uppercase tracking-[0.15em] text-[color:var(--muted-foreground)] opacity-50">
            Active Care Goals
          </div>
          <ul className="space-y-2">
            {overview?.insights.recommendations.slice(0, 2).map((rec, i) => (
              <li key={i} className="flex items-start gap-2 text-xs leading-relaxed text-[color:var(--muted-foreground)]">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[color:var(--accent)]" />
                {rec}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </aside>
  );
}
