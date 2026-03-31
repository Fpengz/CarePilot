import { ComposedChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend, Label } from "recharts";
import { CHART_COLORS, COMMON_AXIS_PROPS, ClinicalTooltip } from "./chart-utils";

export function CorrelationChart({ calories, risk }: { calories: any[]; risk: any[] }) {
  // Merge data based on labels
  const caloriesData = Array.isArray(calories) ? calories : [];
  const riskData = Array.isArray(risk) ? risk : [];

  const data = caloriesData.map((c, i) => ({
    label: c.label,
    calories: c.value,
    risk: riskData[i]?.value
  }));

  return (
    <div className="bg-panel border border-border-soft rounded-3xl p-8 shadow-sm h-full">
      <div className="flex flex-col items-start gap-1 mb-8 px-1">
        <span className="text-micro-label text-muted-foreground uppercase">Correlation Analysis</span>
        <h3 className="text-xl font-semibold tracking-tight text-foreground">Metabolic Response Trends</h3>
      </div>
      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--chart-grid)" strokeOpacity={0.5} />
            <XAxis dataKey="label" {...COMMON_AXIS_PROPS} tickMargin={10} />
            <YAxis yAxisId="left" {...COMMON_AXIS_PROPS} width={40}>
              <Label 
                value="CALORIES (KCAL)" 
                angle={-90} 
                position="insideLeft" 
                style={{ textAnchor: 'middle', fontSize: '8px', fontWeight: 'bold', fill: CHART_COLORS.calories, opacity: 0.8 }} 
              />
            </YAxis>
            <YAxis yAxisId="right" orientation="right" {...COMMON_AXIS_PROPS} width={40}>
              <Label 
                value="RISK SCORE" 
                angle={90} 
                position="insideRight" 
                style={{ textAnchor: 'middle', fontSize: '8px', fontWeight: 'bold', fill: CHART_COLORS.risk, opacity: 0.8 }} 
              />
            </YAxis>
            <Tooltip content={<ClinicalTooltip />} />
            <Legend 
              verticalAlign="top" 
              align="right" 
              iconType="circle" 
              iconSize={6}
              content={({ payload }) => (
                <div className="flex justify-end gap-4 mb-4">
                  {payload?.map((entry: any, index: number) => (
                    <div key={`item-${index}`} className="flex items-center gap-1.5">
                      <div className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: entry.color }} />
                      <span className="text-[9px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)]">
                        {entry.value}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            />
            <Line 
              yAxisId="left" 
              type="monotone" 
              dataKey="calories" 
              name="Calories" 
              stroke={CHART_COLORS.calories} 
              strokeWidth={2.5} 
              dot={false} 
              activeDot={{ r: 4, fill: CHART_COLORS.calories, stroke: 'var(--background)', strokeWidth: 2 }}
            />
            <Line 
              yAxisId="right" 
              type="monotone" 
              dataKey="risk" 
              name="Glycemic Risk" 
              stroke={CHART_COLORS.risk} 
              strokeWidth={2.5} 
              dot={false} 
              activeDot={{ r: 4, fill: CHART_COLORS.risk, stroke: 'var(--background)', strokeWidth: 2 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
