import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
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
    <div className="glass-card h-full">
      <div className="flex flex-col items-start gap-1 mb-6">
        <span className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Blood Pressure</span>
        <h3 className="text-lg font-bold tracking-tight">Trend Overview</h3>
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
                  fontSize: "10px",
                }}
                formatter={(value: number, name: string) => [`${value} mmHg`, name]}
              />
              <Line
                type="monotone"
                dataKey="systolic"
                name="Systolic"
                stroke="#dc2626"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 4, fill: "#dc2626", stroke: "var(--background)", strokeWidth: 2 }}
              />
              <Line
                type="monotone"
                dataKey="diastolic"
                name="Diastolic"
                stroke="#2563eb"
                strokeWidth={2.5}
                dot={false}
                activeDot={{ r: 4, fill: "#2563eb", stroke: "var(--background)", strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-xs text-[color:var(--muted-foreground)] italic">
            {showLoading ? "Loading blood pressure data..." : "No blood pressure data available."}
          </div>
        )}
      </div>
    </div>
  );
}
