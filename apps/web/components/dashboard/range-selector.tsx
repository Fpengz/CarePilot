import { startTransition } from "react";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";

type RangeKey = "today" | "7d" | "30d" | "3m" | "1y" | "custom";

const RANGE_OPTIONS: Array<{ value: RangeKey; label: string }> = [
  { value: "today", label: "Today" },
  { value: "7d", label: "Last 7 Days" },
  { value: "30d", label: "Last 30 Days" },
  { value: "3m", label: "Last 3 Months" },
  { value: "1y", label: "Last Year" },
  { value: "custom", label: "Custom Range" },
];

export function RangeSelector({
  range,
  onRangeChange,
  customRange,
  onCustomRangeChange,
}: {
  range: RangeKey;
  onRangeChange: (range: RangeKey) => void;
  customRange: { from: string; to: string };
  onCustomRangeChange: (next: { from: string; to: string }) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Select
        value={range}
        onChange={(event) => {
          const nextRange = event.target.value as RangeKey;
          startTransition(() => onRangeChange(nextRange));
        }}
        className="h-11 rounded-xl bg-surface border-border-soft shadow-sm text-sm font-semibold transition-all px-4 focus:ring-accent-teal/20"
      >
        {RANGE_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>

      {range === "custom" ? (
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex items-center gap-2 px-3 py-1 bg-panel border border-border-soft rounded-xl shadow-sm">
            <span className="text-micro-label font-bold text-muted-foreground uppercase">From</span>
            <Input
              type="date"
              value={customRange.from}
              onChange={(event) =>
                startTransition(() => onCustomRangeChange({ ...customRange, from: event.target.value }))
              }
              className="border-none bg-transparent shadow-none h-8 text-xs font-bold p-0 focus-visible:ring-0"
            />
          </div>
          <div className="flex items-center gap-2 px-3 py-1 bg-panel border border-border-soft rounded-xl shadow-sm">
            <span className="text-micro-label font-bold text-muted-foreground uppercase">To</span>
            <Input
              type="date"
              value={customRange.to}
              onChange={(event) =>
                startTransition(() => onCustomRangeChange({ ...customRange, to: event.target.value }))
              }
              className="border-none bg-transparent shadow-none h-8 text-xs font-bold p-0 focus-visible:ring-0"
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}

export type { RangeKey };
