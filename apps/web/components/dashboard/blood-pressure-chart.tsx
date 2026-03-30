import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Activity } from "lucide-react";
import type { DashboardBloodPressureChartApi } from "@/lib/types";
import { COMMON_AXIS_PROPS } from "./chart-utils";

export function BloodPressureChart({
  chart,
  loading = false,
}: {
  chart?: DashboardBloodPressureChartApi | null;
  loading?: boolean;
}) {
  const data = chart?.points?.map((point) => ({
    label: point.label,
    systolic: point.systolic,
    diastolic: point.diastolic,
  })) ?? [];
  const hasData = data.some((item) => item.systolic > 0 || item.diastolic > 0);
  const showLoading = loading || !chart;

  return (
    <div className="bg-panel border border-border-soft rounded-3xl p-8 shadow-sm h-full">
      <div className="flex flex-col items-start gap-1 mb-8 px-1">
        <span className="text-micro-label text-muted-foreground uppercase">Blood Pressure</span>
        <h3 className="text-xl font-semibold tracking-tight text-foreground">Vitals Trend Overview</h3>
      </div>
      <div className="flex items-center justify-between mb-4 px-1">
        <span className="text-micro-label text-muted-foreground opacity-60">
          MMHG
        </span>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-2 text-micro-label text-muted-foreground">
            <span className="h-2 w-2 rounded-full bg-rose-500" />
            SYSTOLIC
          </span>
          <span className="flex items-center gap-2 text-micro-label text-muted-foreground">
            <span className="h-2 w-2 rounded-full bg-blue-500" />
            DIASTOLIC
          </span>
        </div>
      </div>
      <div className="h-72 w-full">
        {hasData ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke="var(--chart-grid)" strokeOpacity={0.5} />
              <XAxis dataKey="label" {...COMMON_AXIS_PROPS} tickMargin={10} />
              <YAxis {...COMMON_AXIS_PROPS} width={40} />
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
              <Line
                type="monotone"
                dataKey="systolic"
                name="Systolic"
                stroke="#f43f5e"
                strokeWidth={3}
                dot={false}
                activeDot={{ r: 5, fill: "#f43f5e", stroke: "var(--surface)", strokeWidth: 2 }}
              />
              <Line
                type="monotone"
                dataKey="diastolic"
                name="Diastolic"
                stroke="#3b82f6"
                strokeWidth={3}
                dot={false}
                activeDot={{ r: 5, fill: "#3b82f6", stroke: "var(--surface)", strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-sm text-muted-foreground italic bg-surface/50 rounded-2xl border border-dashed border-border-soft">
            <Activity className="h-8 w-8 mb-2 opacity-20" />
            {showLoading ? "Synchronizing vitals..." : "No blood pressure records found."}
          </div>
        )}
      </div>
    </div>
  );
}
