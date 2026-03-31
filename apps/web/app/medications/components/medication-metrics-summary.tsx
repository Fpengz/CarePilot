import { CheckCircle2, AlertCircle, Calendar } from "lucide-react";

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
    <div className="py-2">
      <div className="flex flex-col gap-10 lg:flex-row lg:items-end justify-between border-b border-border-soft pb-12">
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-accent-teal">Clinical Adherence</span>
          </div>
          <div className="flex items-baseline gap-4">
            <h3 className="text-6xl font-bold tracking-tighter text-foreground">
              {loading ? "..." : Math.round(adherenceRate)}<span className="text-3xl text-muted-foreground ml-1">%</span>
            </h3>
            <div className="pb-2">
              <p className="text-[13px] text-muted-foreground font-medium max-w-[240px] leading-relaxed">
                Adherence score based on the last 30 days of scheduled clinical events.
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-8 lg:gap-16">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-health-teal">
              <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="text-[10px] font-bold uppercase tracking-widest opacity-80">Taken</span>
            </div>
            <div className="text-2xl font-semibold tracking-tight">{loading ? "..." : taken}</div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2 text-health-rose">
              <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="text-[10px] font-bold uppercase tracking-widest opacity-80">Missed</span>
            </div>
            <div className="text-2xl font-semibold tracking-tight">{loading ? "..." : missed}</div>
          </div>

          <div className="space-y-2 col-span-2 md:col-span-1">
            <div className="flex items-center gap-2 text-muted-foreground/60">
              <Calendar className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="text-[10px] font-bold uppercase tracking-widest opacity-80">Scheduled</span>
            </div>
            <div className="text-2xl font-semibold tracking-tight">{loading ? "..." : totalEvents}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
