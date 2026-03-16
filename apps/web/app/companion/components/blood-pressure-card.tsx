"use client";

import { Activity, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { BloodPressureChartApi, BloodPressureSummaryApi } from "@/lib/types";
import { COMMON_AXIS_PROPS } from "@/components/dashboard/chart-utils";

interface BloodPressureCardProps {
  summary: BloodPressureSummaryApi | null | undefined;
  loading?: boolean;
  chart?: BloodPressureChartApi | null | undefined;
}

function trendIcon(direction: BloodPressureSummaryApi["trend"]["direction"]) {
  if (direction === "increase") return <TrendingUp className="h-3.5 w-3.5 text-health-rose" />;
  if (direction === "decrease") return <TrendingDown className="h-3.5 w-3.5 text-health-teal" />;
  return <Minus className="h-3.5 w-3.5 text-[color:var(--muted-foreground)]" />;
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
    <Card className="shadow-sm rounded-xl overflow-hidden">
      <CardHeader className="bg-[color:var(--panel-soft)] border-b border-[color:var(--border-soft)] pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[color:var(--accent)]/10 text-[color:var(--accent)]">
              <Activity className="h-4 w-4" />
            </div>
            <div>
              <CardTitle className="text-base font-bold text-[color:var(--foreground)]">Blood Pressure Analysis</CardTitle>
              <CardDescription className="text-[10px] font-medium uppercase tracking-tight">Recent Longitudinal Signals</CardDescription>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-6">
        {summary ? (
          <div className="space-y-6">
            <div className="flex items-end justify-between">
              <div className="space-y-1">
                <span className="text-[10px] font-bold text-[color:var(--muted-foreground)] uppercase tracking-widest">Average Reading</span>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-3xl font-black tracking-tighter text-[color:var(--foreground)] font-mono">
                    {summary.stats.avg_systolic.toFixed(0)}/{summary.stats.avg_diastolic.toFixed(0)}
                  </span>
                  <span className="text-xs font-bold text-[color:var(--muted-foreground)] uppercase">mmHg</span>
                </div>
              </div>
              <div className="flex flex-col items-end gap-1">
                <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-[color:var(--panel-soft)] border border-[color:var(--border-soft)] shadow-sm">
                  {trendIcon(summary.trend.direction)}
                  <span className="text-[10px] font-bold text-[color:var(--muted-foreground)] uppercase tracking-tighter">
                    {summary.trend.direction} (Δ{summary.trend.delta_systolic.toFixed(1)})
                  </span>
                </div>
                <span className="text-[9px] font-bold text-[color:var(--muted-foreground)]/70 uppercase tracking-widest">Trend over {summary.stats.total_readings} reads</span>
              </div>
            </div>

            {hasChart ? (
              <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-4">
                <div className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)] mb-3">
                  Blood Pressure Trend
                </div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[9px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">
                    mmHg
                  </span>
                  <div className="flex items-center gap-3 text-[9px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">
                    <span className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-[#dc2626]" />
                      Systolic
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-[#2563eb]" />
                      Diastolic
                    </span>
                  </div>
                </div>
                <div className="h-28 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartPoints} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                      <CartesianGrid vertical={false} stroke="var(--chart-grid)" strokeOpacity={0.5} />
                      <XAxis dataKey="label" {...COMMON_AXIS_PROPS} tickMargin={6} />
                      <YAxis {...COMMON_AXIS_PROPS} width={28} />
                      <Tooltip
                        contentStyle={{
                          background: "var(--surface)",
                          borderColor: "var(--border-soft)",
                          fontSize: "10px",
                        }}
                        formatter={(value: any, name: any) => [`${value} mmHg`, name]}
                      />
                      <Line type="monotone" dataKey="systolic" name="Systolic" stroke="#dc2626" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="diastolic" name="Diastolic" stroke="#2563eb" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            ) : null}

            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--panel-soft)] p-3 flex flex-col items-center text-center">
                <span className="text-[9px] font-bold text-[color:var(--muted-foreground)] uppercase tracking-widest mb-1">Target</span>
                <span className="text-sm font-bold text-[color:var(--foreground)] font-mono">{summary.target_systolic}/{summary.target_diastolic}</span>
              </div>
              <div className={`rounded-xl border p-3 flex flex-col items-center text-center ${summary.above_target ? 'bg-health-rose-soft border-health-rose/20' : 'bg-health-teal-soft border-health-teal/20'}`}>
                <span className={`text-[9px] font-bold uppercase tracking-widest mb-1 ${summary.above_target ? 'text-health-rose' : 'text-health-teal'}`}>Control</span>
                <span className={`text-sm font-bold font-mono ${summary.above_target ? 'text-health-rose' : 'text-health-teal'}`}>{summary.above_target ? 'Above' : 'Within'}</span>
              </div>
              <div className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--panel-soft)] p-3 flex flex-col items-center text-center">
                <span className="text-[9px] font-bold text-[color:var(--muted-foreground)] uppercase tracking-widest mb-1">Risk Reads</span>
                <span className="text-sm font-bold text-[color:var(--foreground)] font-mono">{summary.abnormal_readings.length}</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="py-12 text-center border border-dashed border-[color:var(--border-soft)] rounded-2xl bg-[color:var(--panel-soft)]">
            <Activity className="h-8 w-8 text-[color:var(--muted-foreground)]/40 mx-auto mb-3" />
            <p className="text-xs text-[color:var(--muted-foreground)] italic">
              {loading ? "Loading blood pressure readings..." : "Insufficient paired data for trend analysis."}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
