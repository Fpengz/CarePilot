import type { DashboardMetricChartApi } from "@/lib/types";

export function TrendPanel({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-5">
      <div className="space-y-2">
        <div className="text-sm font-semibold text-[color:var(--foreground)]">{title}</div>
        <p className="text-sm text-[color:var(--muted-foreground)]">{description}</p>
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

export type { DashboardMetricChartApi };
