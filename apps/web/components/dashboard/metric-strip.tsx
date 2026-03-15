import { Activity, CheckCircle, Zap, Target } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";

interface MetricItemProps {
  label: string;
  value: string;
  unit?: string;
  data: any[];
  icon: React.ReactNode;
}

function MetricItem({ label, value, unit, data, icon }: MetricItemProps) {
  return (
    <div className="flex flex-1 flex-col items-start gap-1 px-4 first:pl-0 last:pr-0 border-r border-white/10 last:border-0">
      <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">
        {icon}
        <span>{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-xl font-bold tracking-tight">{value}</span>
        {unit && <span className="text-xs font-medium text-[color:var(--muted-foreground)]">{unit}</span>}
      </div>
      <div className="h-4 mt-1 w-full opacity-50">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <Area type="monotone" dataKey="value" stroke="var(--primary)" fill="var(--primary)" fillOpacity={0.1} strokeWidth={1.5} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function MetricStrip({ overview, sparklines }: { overview: any; sparklines: any }) {
  return (
    <div className="glass-card col-span-12 !py-4 flex items-center divide-x divide-white/5 overflow-x-auto scrollbar-hide">
      <MetricItem 
        label="Signal" 
        value={overview.summary.adherence_score.value > 80 ? "Stable" : "Variable"} 
        icon={<Activity className="h-3 w-3" />}
        data={sparklines.adherence}
      />
      <MetricItem 
        label="Adherence" 
        value={Math.round(overview.summary.adherence_score.value).toString()} 
        unit="%" 
        icon={<CheckCircle className="h-3 w-3" />}
        data={sparklines.adherence}
      />
      <MetricItem 
        label="Risk" 
        value={Math.round(overview.summary.glycemic_risk.value).toString()} 
        unit="/100" 
        icon={<Zap className="h-3 w-3" />}
        data={sparklines.risk}
      />
      <MetricItem 
        label="Goal" 
        value={Math.round(overview.summary.nutrition_goal_score.value).toString()} 
        unit="%" 
        icon={<Target className="h-3 w-3" />}
        data={sparklines.nutrition}
      />
    </div>
  );
}
