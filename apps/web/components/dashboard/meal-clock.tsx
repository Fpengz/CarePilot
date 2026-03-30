import { PolarGrid, PolarAngleAxis, Radar, RadarChart, ResponsiveContainer } from "recharts";
import { CHART_COLORS } from "./chart-utils";

export function MealClock({ bins }: { bins: { hour: number; count: number }[] }) {
  return (
    <div className="bg-panel border border-border-soft rounded-3xl p-8 shadow-sm h-full">
      <div className="flex flex-col items-start gap-1 mb-8 px-1">
        <span className="text-micro-label text-muted-foreground uppercase">Circadian Rhythms</span>
        <h3 className="text-xl font-semibold tracking-tight text-foreground">Meal Timing Density</h3>
      </div>
      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="80%" data={bins}>
            <PolarGrid stroke="var(--chart-grid)" strokeOpacity={0.5} />
            <PolarAngleAxis dataKey="hour" fontSize={9} fontWeight="bold" tick={{ fill: 'var(--chart-text)' }} />
            <Radar 
              name="Meals" 
              dataKey="count" 
              stroke={CHART_COLORS.carbs} 
              fill={CHART_COLORS.carbs} 
              fillOpacity={0.4} 
              strokeWidth={2}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
