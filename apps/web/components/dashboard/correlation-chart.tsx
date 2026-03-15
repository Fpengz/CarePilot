import { ComposedChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { CHART_COLORS, COMMON_AXIS_PROPS, ClinicalTooltip } from "./chart-utils";

export function CorrelationChart({ calories, risk }: { calories: any[]; risk: any[] }) {
  // Merge data based on labels
  const data = calories.map((c, i) => ({
    label: c.label,
    calories: c.value,
    risk: risk[i]?.value
  }));

  return (
    <div className="glass-card h-full">
      <div className="flex flex-col items-start gap-1 mb-6">
        <span className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Metabolic Data</span>
        <h3 className="text-lg font-bold tracking-tight">Correlation Analysis</h3>
      </div>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data}>
            <CartesianGrid vertical={false} stroke="var(--chart-grid)" strokeOpacity={0.5} />
            <XAxis dataKey="label" {...COMMON_AXIS_PROPS} />
            <YAxis yAxisId="left" {...COMMON_AXIS_PROPS} />
            <YAxis yAxisId="right" orientation="right" {...COMMON_AXIS_PROPS} />
            <Tooltip content={<ClinicalTooltip />} />
            <Line 
              yAxisId="left" 
              type="monotone" 
              dataKey="calories" 
              name="Calories" 
              stroke={CHART_COLORS.calories} 
              strokeWidth={2.5} 
              dot={false} 
            />
            <Line 
              yAxisId="right" 
              type="monotone" 
              dataKey="risk" 
              name="Glycemic Risk" 
              stroke={CHART_COLORS.risk} 
              strokeWidth={2.5} 
              dot={false} 
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
