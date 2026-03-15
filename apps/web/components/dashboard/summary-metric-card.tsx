import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { formatChartValue } from "./chart-utils";

export function SummaryMetricCard({ label, value, unit, data }: { label: string; value: number; unit: string; data: any[] }) {
  return (
    <div className="glass-card">
      <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[color:var(--muted-foreground)] mb-1">{label}</div>
      <div className="flex items-baseline gap-1">
        <span className="text-3xl font-bold tracking-tight">{formatChartValue(value)}</span>
        <span className="text-sm font-medium text-[color:var(--muted-foreground)]">{value !== 0 ? unit : ""}</span>
      </div>
...
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <Area type="monotone" dataKey="value" stroke="var(--primary)" fill="var(--primary)" fillOpacity={0.1} strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
