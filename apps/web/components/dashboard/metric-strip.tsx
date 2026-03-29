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
    <div className="flex flex-1 flex-col items-center gap-1 px-4 first:pl-0 last:pr-0 border-r border-white/5 last:border-0 text-center">
      <div className="flex items-center gap-2 text-[9px] font-bold uppercase tracking-[0.2em] text-[color:var(--muted-foreground)] opacity-60">
        {icon}
        <span>{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-xl font-bold tracking-tight tabular-nums">{value}</span>
        {unit && <span className="text-[10px] font-bold text-[color:var(--muted-foreground)] opacity-60">{unit}</span>}
      </div>
      <div className="h-3 mt-1 w-full max-w-[60px] opacity-40">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <Area type="monotone" dataKey="value" stroke="var(--primary)" fill="var(--primary)" fillOpacity={0.1} strokeWidth={1.5} />
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
    <div className="glass-card col-span-12 !py-5 flex items-center justify-between divide-x divide-white/5 overflow-hidden">
      <MetricItem 
        label="Signal" 
        value={overview.summary.adherence_score.value > 80 ? "Stable" : "Variable"} 
        icon={<Activity className="h-3 w-3" />}
        data={sparklineFrom(charts.adherence)}
      />
      <MetricItem 
        label="Adherence" 
        value={Math.round(overview.summary.adherence_score.value).toString()} 
        unit="%" 
        icon={<CheckCircle className="h-3 w-3" />}
        data={sparklineFrom(charts.adherence)}
      />
      <MetricItem 
        label="Risk" 
        value={Math.round(overview.summary.glycemic_risk.value).toString()} 
        unit="/100" 
        icon={<Zap className="h-3 w-3" />}
        data={sparklineFrom(charts.glycemic_risk)}
      />
      <MetricItem 
        label="Goal" 
        value={Math.round(overview.summary.nutrition_goal_score.value).toString()} 
        unit="%" 
        icon={<Target className="h-3 w-3" />}
        data={sparklineFrom(charts.calories)}
      />
    </div>
  );
}
