import { TooltipProps } from 'recharts';
import { NameType, ValueType } from 'recharts/types/component/DefaultTooltipContent';

export const CHART_COLORS = {
  protein: "#f59e0b",
  carbs: "#047857",
  fat: "#9333ea",
  calories: "#c2410c",
  risk: "#dc2626",
};

export const COMMON_AXIS_PROPS = {
  stroke: "var(--chart-text)",
  fontSize: 9,
  fontWeight: "bold",
  tickLine: false,
  axisLine: false,
};

export const ClinicalTooltip = ({ active, payload, label }: TooltipProps<ValueType, NameType>) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-xl border border-[color:var(--chart-grid)] bg-[color:var(--chart-bg)] p-3 shadow-xl backdrop-blur-md">
        <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)]">{label}</p>
        <div className="space-y-1.5">
          {payload.map((entry) => (
            <div key={entry.name} className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <div className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: entry.color }} />
                <span className="text-xs font-medium text-[color:var(--foreground)]">{entry.name}</span>
              </div>
              <span className="text-xs font-bold tabular-nums text-[color:var(--foreground)]">
                {entry.value}{entry.unit || 'g'}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};
