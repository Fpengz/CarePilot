"use client";

import { CheckCircle2, AlertCircle, Calendar, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

interface MedicationMetricsSummaryProps {
  adherenceRate: number;
  totalEvents: number;
  taken: number;
  missed: number;
  loading?: boolean;
}

export function MedicationMetricsSummary({
  adherenceRate,
  totalEvents,
  taken,
  missed,
  loading
}: MedicationMetricsSummaryProps) {
  return (
    <div className="clinical-card">
      <div className="flex flex-col gap-8 md:flex-row md:items-center">
        <div className="flex-1 space-y-4">
          <div className="flex items-center gap-2">
            <span className="clinical-kicker">Clinical Adherence</span>
          </div>
          <h3 className="text-3xl font-bold tracking-tight">
            {loading ? "..." : `${Math.round(adherenceRate)}%`}
          </h3>
          <p className="clinical-body max-w-sm">
            Your adherence score is based on the last 30 days of scheduled medication events.
          </p>
        </div>

        <div className="grid flex-[2] gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-4 space-y-3">
            <div className="flex items-center gap-2 text-emerald-500">
              <CheckCircle2 className="h-4 w-4" />
              <span className="text-[10px] font-bold uppercase tracking-wider opacity-70">Taken</span>
            </div>
            <div className="text-xl font-bold">{loading ? "..." : taken}</div>
          </div>

          <div className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-4 space-y-3">
            <div className="flex items-center gap-2 text-rose-500">
              <AlertCircle className="h-4 w-4" />
              <span className="text-[10px] font-bold uppercase tracking-wider opacity-70">Missed</span>
            </div>
            <div className="text-xl font-bold">{loading ? "..." : missed}</div>
          </div>

          <div className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-4 space-y-3">
            <div className="flex items-center gap-2 text-[color:var(--accent)]">
              <Calendar className="h-4 w-4" />
              <span className="text-[10px] font-bold uppercase tracking-wider opacity-70">Total Scheduled</span>
            </div>
            <div className="text-xl font-bold">{loading ? "..." : totalEvents}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
