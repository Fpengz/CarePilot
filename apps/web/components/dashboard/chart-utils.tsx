import { TooltipProps } from "recharts";
import { NameType, ValueType } from "recharts/types/component/DefaultTooltipContent";

export const CHART_COLORS = {
  protein: "#f59e0b",
  carbs: "#047857",
  fat: "#9333ea",
  calories: "#4338ca", // Indigo for metabolic intake
  risk: "#be123c",    // Rose for glycemic risk
};

export const COMMON_AXIS_PROPS = {
  stroke: "var(--chart-text)",
  fontSize: 9,
  fontWeight: "bold",
  tickLine: false,
  axisLine: false,
};

export const formatChartValue = (value: number) => {
  if (value === 0) return "-";
  return Math.round(value).toString();
};

type ClinicalTooltipPayloadEntry = {
  name?: string | number;
  value?: number | string;
  color?: string;
  unit?: string;
};

type ClinicalTooltipProps = TooltipProps<ValueType, NameType> & {
  payload?: ClinicalTooltipPayloadEntry[];
  label?: string | number;
};

export const ClinicalTooltip = ({ active, payload, label }: ClinicalTooltipProps) => {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-xl border border-white/20 bg-white/40 dark:bg-black/40 p-3 shadow-2xl backdrop-blur-[20px]">
        <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)]">{label}</p>
        <div className="space-y-1.5">
          {payload.map((entry, index) => (
            <div key={`${entry.name ?? "metric"}-${index}`} className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <div className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: entry.color }} />
                <span className="text-xs font-medium text-[color:var(--foreground)]">{entry.name}</span>
              </div>
              <span className="text-xs font-bold tabular-nums text-[color:var(--foreground)]">
                {entry.value === 0 ? "-" : entry.value}
                {entry.value !== 0 ? entry.unit || "g" : ""}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};
