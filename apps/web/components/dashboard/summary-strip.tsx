import type { DashboardSummaryMetricApi } from "@/lib/types";

function formatMetric(metric: DashboardSummaryMetricApi): string {
  if (metric.unit === "%") return `${Math.round(metric.value)}%`;
  if (metric.unit === "/100") return `${Math.round(metric.value)}/100`;
  return `${Math.round(metric.value)}${metric.unit ? ` ${metric.unit}` : ""}`;
}

function formatSigned(value: number, suffix = ""): string {
  const rounded = Math.round(value * 10) / 10;
  if (rounded === 0) return `0${suffix}`;
  return `${rounded > 0 ? "+" : ""}${rounded}${suffix}`;
}

export function SummaryStrip({
  metrics,
}: {
  metrics: DashboardSummaryMetricApi[];
}) {
  return (
    <div className="grid gap-4 rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-5 sm:grid-cols-3">
      {metrics.map((metric) => (
        <div key={metric.label} className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-[color:var(--muted-foreground)]">
            {metric.label}
          </div>
          <div className="flex items-baseline gap-3">
            <div className="text-2xl font-semibold text-[color:var(--foreground)]">
              {formatMetric(metric)}
            </div>
            <div className="text-xs text-[color:var(--muted-foreground)]">
              {formatSigned(metric.delta, metric.unit === "%" ? "%" : "")}
            </div>
          </div>
          {metric.detail ? (
            <div className="text-sm text-[color:var(--muted-foreground)]">
              {metric.detail}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
