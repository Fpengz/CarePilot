import { Activity, CheckCircle, Zap, Target } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import type { DashboardChartsApi } from "@/lib/types";

interface MetricItemProps {
  label: string;
  value: string;
  unit?: string;
  data: any[];
  icon: React.ReactNode;
}

function MetricItem({ label, value, unit, data, icon }: MetricItemProps) {
  return (
    <div className="flex flex-1 flex-col items-center gap-1.5 px-6 first:pl-0 last:pr-0 border-r border-border-soft last:border-0 text-center group transition-all hover:bg-white/40 dark:hover:bg-black/20 py-2">
      <div className="flex items-center gap-2 text-micro-label text-muted-foreground opacity-80 group-hover:opacity-100 transition-opacity">
        {icon}
        <span>{label}</span>
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className="text-2xl font-semibold tracking-tight tabular-nums text-foreground">{value}</span>
        {unit && <span className="text-[11px] font-bold text-muted-foreground opacity-60">{unit}</span>}
      </div>
      <div className="h-4 mt-1 w-full max-w-[80px] opacity-60 group-hover:opacity-100 transition-all">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <Area type="monotone" dataKey="value" stroke="var(--accent-teal)" fill="var(--accent-teal)" fillOpacity={0.1} strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function MetricStrip({
  overview,
  charts,
}: {
  overview: any;
  charts: DashboardChartsApi;
}) {
  const sparklineFrom = (chart?: { points?: unknown }) =>
    Array.isArray(chart?.points) ? chart.points : [];

  return (
    <div className="col-span-12 rounded-2xl border border-border-soft bg-panel shadow-sm px-6 py-4 flex items-center justify-between overflow-hidden">
      <MetricItem 
        label="Health Signal" 
        value={overview.summary.adherence_score.value > 80 ? "Stable" : "Variable"} 
        icon={<Activity className="h-3.5 w-3.5 text-accent-teal" />}
        data={sparklineFrom(charts.adherence)}
      />
      <MetricItem 
        label="Adherence" 
        value={Math.round(overview.summary.adherence_score.value).toString()} 
        unit="%" 
        icon={<CheckCircle className="h-3.5 w-3.5 text-accent-teal" />}
        data={sparklineFrom(charts.adherence)}
      />
      <MetricItem 
        label="Glycemic Risk" 
        value={Math.round(overview.summary.glycemic_risk.value).toString()} 
        unit="/100" 
        icon={<Zap className="h-3.5 w-3.5 text-accent-teal" />}
        data={sparklineFrom(charts.glycemic_risk)}
      />
      <MetricItem 
        label="Nutrition Goal" 
        value={Math.round(overview.summary.nutrition_goal_score.value).toString()} 
        unit="%" 
        icon={<Target className="h-3.5 w-3.5 text-accent-teal" />}
        data={sparklineFrom(charts.calories)}
      />
    </div>
  );
}
