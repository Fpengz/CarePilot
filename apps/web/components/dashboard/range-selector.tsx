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
    <div className="flex flex-wrap items-center gap-4">
      <Select
        value={range}
        onChange={(event) => {
          const nextRange = event.target.value as RangeKey;
          startTransition(() => onRangeChange(nextRange));
        }}
      >
        {RANGE_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>

      {range === "custom" ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="space-y-2 text-sm">
            <span className="font-medium text-[color:var(--foreground)]">From</span>
            <Input
              type="date"
              value={customRange.from}
              onChange={(event) =>
                startTransition(() => onCustomRangeChange({ ...customRange, from: event.target.value }))
              }
            />
          </label>
          <label className="space-y-2 text-sm">
            <span className="font-medium text-[color:var(--foreground)]">To</span>
            <Input
              type="date"
              value={customRange.to}
              onChange={(event) =>
                startTransition(() => onCustomRangeChange({ ...customRange, to: event.target.value }))
              }
            />
          </label>
        </div>
      ) : null}
    </div>
  );
}

export type { RangeKey };
