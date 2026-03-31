import { PolarGrid, PolarAngleAxis, Radar, RadarChart, ResponsiveContainer } from "recharts";
import { CHART_COLORS } from "./chart-utils";

export function MealClock({ bins }: { bins: { hour: number; count: number }[] }) {
  const chartData = Array.isArray(bins) ? bins : [];

  return (
    <div className="glass-card h-full">
      <div className="flex flex-col items-start gap-1 mb-6">
        <span className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Circadian Rhythms</span>
        <h3 className="text-lg font-bold tracking-tight">Meal Timing (24h)</h3>
      </div>
      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="80%" data={chartData}>
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
