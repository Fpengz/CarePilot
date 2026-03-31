"use client";

import { Activity, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";
import { cn } from "@/lib/utils";
import type { BloodPressureChartApi, BloodPressureSummaryApi } from "@/lib/types";
import { COMMON_AXIS_PROPS } from "@/components/dashboard/chart-utils";

interface BloodPressureCardProps {
  summary: BloodPressureSummaryApi | null | undefined;
  loading?: boolean;
  chart?: BloodPressureChartApi | null | undefined;
}

function trendIcon(direction: BloodPressureSummaryApi["trend"]["direction"]) {
  if (direction === "increase") return <TrendingUp className="h-3.5 w-3.5 text-rose-600" />;
  if (direction === "decrease") return <TrendingDown className="h-3.5 w-3.5 text-accent-teal" />;
  return <Minus className="h-3.5 w-3.5 text-muted-foreground opacity-40" />;
}

export function BloodPressureCard({ summary, loading = false, chart }: BloodPressureCardProps) {
  const chartPoints =
    chart?.points?.map((point) => ({
      label: point.label,
      systolic: point.systolic,
      diastolic: point.diastolic,
    })) ?? [];
  const hasChart = chartPoints.some((point) => point.systolic > 0 || point.diastolic > 0);

  return (
    <div className="bg-panel border border-border-soft rounded-3xl overflow-hidden shadow-sm h-full flex flex-col">
      <div className="bg-panel/50 border-b border-border-soft px-6 py-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-accent-teal/10 text-accent-teal border border-accent-teal/20 shadow-sm">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-foreground">Blood Pressure Analysis</h3>
              <p className="text-micro-label font-bold text-muted-foreground uppercase tracking-tight opacity-60">Longitudinal Clinical Signals</p>
            </div>
          </div>
        </div>
      </div>
      
      <div className="p-6 space-y-8 flex-1">
        {summary ? (
          <div className="space-y-8">
            <div className="flex items-end justify-between px-1">
              <div className="space-y-2">
                <span className="text-micro-label font-bold text-muted-foreground uppercase tracking-widest">Average Composite</span>
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-bold tracking-tighter text-foreground font-mono">
                    {summary.stats.avg_systolic.toFixed(0)}/{summary.stats.avg_diastolic.toFixed(0)}
                  </span>
                  <span className="text-xs font-bold text-muted-foreground uppercase">mmHg</span>
                </div>
              </div>
              <div className="flex flex-col items-end gap-2">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface border border-border-soft shadow-sm">
                  {trendIcon(summary.trend.direction)}
                  <span className="text-micro-label font-bold text-foreground uppercase tracking-tighter">
                    {summary.trend.direction} (Δ{summary.trend.delta_systolic.toFixed(1)})
                  </span>
                </div>
                <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest opacity-60">
                  {summary.stats.total_readings} historical reads
                </span>
              </div>
            </div>

            {hasChart ? (
              <div className="rounded-3xl border border-border-soft bg-surface p-6 shadow-sm">
                <div className="flex items-center justify-between mb-6">
                  <span className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground opacity-60">
                    Baseline Correlation
                  </span>
                  <div className="flex items-center gap-4">
                    <span className="flex items-center gap-2 text-micro-label text-muted-foreground font-bold">
                      <span className="h-2 w-2 rounded-full bg-rose-500" />
                      SYS
                    </span>
                    <span className="flex items-center gap-2 text-micro-label text-muted-foreground font-bold">
                      <span className="h-2 w-2 rounded-full bg-blue-500" />
                      DIA
                    </span>
                  </div>
                </div>
                <div className="h-32 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartPoints} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                      <CartesianGrid vertical={false} stroke="var(--chart-grid)" strokeOpacity={0.5} />
                      <XAxis dataKey="label" {...COMMON_AXIS_PROPS} tickMargin={8} />
                      <YAxis {...COMMON_AXIS_PROPS} width={32} />
                      <Tooltip
                        contentStyle={{
                          background: "var(--surface)",
                          borderColor: "var(--border-soft)",
                          borderRadius: "12px",
                          fontSize: "11px",
                          boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)",
                        }}
                        formatter={(value: any, name: any) => [`${value} mmHg`, name]}
                      />
                      <Line type="monotone" dataKey="systolic" name="Systolic" stroke="#f43f5e" strokeWidth={3} dot={false} activeDot={{ r: 4 }} />
                      <Line type="monotone" dataKey="diastolic" name="Diastolic" stroke="#3b82f6" strokeWidth={3} dot={false} activeDot={{ r: 4 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            ) : null}

            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-2xl border border-border-soft bg-panel/50 p-4 flex flex-col items-center text-center group hover:bg-panel transition-colors">
                <span className="text-micro-label font-bold text-muted-foreground uppercase tracking-widest mb-2 opacity-60">Clinical Target</span>
                <span className="text-base font-bold text-foreground font-mono">{summary.target_systolic}/{summary.target_diastolic}</span>
              </div>
              <div className={cn(
                "rounded-2xl border p-4 flex flex-col items-center text-center transition-all",
                summary.above_target ? "bg-rose-50 border-rose-100" : "bg-emerald-50 border-emerald-100"
              )}>
                <span className={cn(
                  "text-micro-label font-bold uppercase tracking-widest mb-2",
                  summary.above_target ? "text-rose-600" : "text-emerald-600"
                )}>Status</span>
                <span className={cn(
                  "text-base font-bold font-mono",
                  summary.above_target ? "text-rose-600" : "text-emerald-600"
                )}>{summary.above_target ? 'ABOVE' : 'WITHIN'}</span>
              </div>
              <div className="rounded-2xl border border-border-soft bg-panel/50 p-4 flex flex-col items-center text-center group hover:bg-panel transition-colors">
                <span className="text-micro-label font-bold text-muted-foreground uppercase tracking-widest mb-2 opacity-60">Risk Reads</span>
                <span className="text-base font-bold text-foreground font-mono">{summary.abnormal_readings.length}</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center py-16 text-center bg-surface/50 rounded-2xl border border-dashed border-border-soft">
            <Activity className="h-10 w-10 text-muted-foreground opacity-20 mb-3" />
            <p className="text-sm text-muted-foreground italic max-w-[200px] mx-auto leading-relaxed">
              {loading ? "Synchronizing readings..." : "Insufficient longitudinal data for trend analysis."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
