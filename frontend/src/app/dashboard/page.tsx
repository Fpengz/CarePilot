"use client";
import { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type DataPoint = { date: string; value: number };
type MetricGroup = { label: string; unit: string; data: DataPoint[] };
type ChartData = { metrics: Record<string, MetricGroup> };
type RawEntry = { datetime: string; message: string };
type TrendResult = {
  change: number;
  pct: number;
  direction: "up" | "down" | "flat";
};
type TrendsData = Record<string, TrendResult>;

function toShortDate(iso: string) {
  // "2026-03-01T10:00:00" → "Mar 1"
  const d = new Date(iso);
  return d.toLocaleDateString("en-SG", { month: "short", day: "numeric" });
}

const COLORS = [
  "#2563eb",
  "#16a34a",
  "#dc2626",
  "#9333ea",
  "#ea580c",
  "#0891b2",
];

export default function DashboardPage() {
  const today = new Date().toISOString().slice(0, 10);
  const monthAgo = new Date(Date.now() - 30 * 86400_000)
    .toISOString()
    .slice(0, 10);

  const [start, setStart] = useState(monthAgo);
  const [end, setEnd] = useState(today);
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [rawEntries, setRawEntries] = useState<RawEntry[]>([]);
  const [trends, setTrends] = useState<TrendsData>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const generate = async () => {
    setLoading(true);
    setError("");
    setTrends({});
    try {
      const [chartRes, entriesRes] = await Promise.all([
        fetch(`${API_BASE}/api/dashboard/chart-data?start=${start}&end=${end}`),
        fetch(`${API_BASE}/api/dashboard/entries?start=${start}&end=${end}`),
      ]);
      const chart: ChartData = await chartRes.json();
      const entries = await entriesRes.json();
      setChartData(chart);
      setRawEntries(entries.entries ?? []);

      // Build first/last payload for trend computation
      const metricsPayload: Record<
        string,
        { first: number; last: number; unit: string }
      > = {};
      for (const [key, group] of Object.entries(chart.metrics ?? {})) {
        if (group.data.length >= 2) {
          metricsPayload[key] = {
            first: group.data[0].value,
            last: group.data[group.data.length - 1].value,
            unit: group.unit ?? "",
          };
        }
      }

      if (Object.keys(metricsPayload).length > 0) {
        const trendRes = await fetch(`${API_BASE}/api/dashboard/trend`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ metrics: metricsPayload }),
        });
        const trendData = await trendRes.json();
        setTrends(trendData.trends ?? {});
      }
    } catch {
      setError("⚠ Could not reach the server. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const metricEntries = chartData ? Object.entries(chartData.metrics) : [];

  return (
    <div className="max-w-5xl mx-auto w-full px-4 py-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-800">📊 Health Dashboard</h1>
      <p className="text-sm text-gray-500">
        Log health metrics in Chat with{" "}
        <code className="bg-blue-50 text-blue-600 px-1 rounded">[TRACK]</code>,
        e.g.{" "}
        <code className="bg-gray-100 rounded px-1">[TRACK] weight 80 kg</code> ·{" "}
        <code className="bg-gray-100 rounded px-1">[TRACK] bp 135/88 mmHg</code>
      </p>

      {/* Date range + generate */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 flex flex-wrap gap-4 items-end">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-500">
            Start date
          </label>
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-300"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium text-gray-500">End date</label>
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-300"
          />
        </div>
        <button
          onClick={generate}
          disabled={loading}
          className="px-5 py-2 rounded-full bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-40 transition-colors"
        >
          {loading ? "Loading…" : "📈 Generate Chart"}
        </button>
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}

      {/* Charts */}
      {metricEntries.length === 0 && chartData && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-10 text-center text-gray-400 text-sm">
          No [TRACK] entries found in this date range.
          <br />
          Send a message like{" "}
          <code className="bg-gray-100 rounded px-1">
            [TRACK] weight 80 kg
          </code>{" "}
          in Chat.
        </div>
      )}

      {metricEntries.map(([metricType, group], idx) => {
        const chartPoints = group.data.map((p) => ({
          date: toShortDate(p.date),
          value: p.value,
        }));
        const color = COLORS[idx % COLORS.length];

        return (
          <div
            key={metricType}
            className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5"
          >
            <div className="flex items-start justify-between mb-4">
              <h2 className="text-base font-semibold text-gray-700">
                {group.label}
                {group.unit && (
                  <span className="text-gray-400 font-normal text-sm ml-1">
                    ({group.unit})
                  </span>
                )}
              </h2>
              {trends[metricType] &&
                (() => {
                  const t = trends[metricType];
                  const isUp = t.direction === "up";
                  const isDown = t.direction === "down";
                  const sign = isUp ? "+" : "";
                  const arrow = isUp ? "▲" : isDown ? "▼" : "→";
                  const colorClass = isUp
                    ? "bg-red-50 text-red-600 border-red-200"
                    : isDown
                      ? "bg-green-50 text-green-600 border-green-200"
                      : "bg-gray-50 text-gray-500 border-gray-200";
                  return (
                    <div
                      className={`flex flex-col items-end gap-0.5 text-xs font-medium border rounded-xl px-3 py-1.5 ${colorClass}`}
                    >
                      <span>
                        {arrow} {sign}
                        {t.change} {group.unit}
                      </span>
                      <span className="font-normal opacity-75">
                        {sign}
                        {t.pct}% over period
                      </span>
                    </div>
                  );
                })()}
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart
                data={chartPoints}
                margin={{ top: 4, right: 20, left: 0, bottom: 4 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis
                  tick={{ fontSize: 12 }}
                  unit={group.unit ? ` ${group.unit}` : ""}
                />
                <Tooltip
                  formatter={(val: number) => [
                    `${val} ${group.unit}`.trim(),
                    group.label,
                  ]}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={color}
                  strokeWidth={2.5}
                  dot={{ r: 4, fill: color }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        );
      })}

      {/* Raw entries table */}
      {rawEntries.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
          <h2 className="text-base font-semibold text-gray-700 mb-4">
            Raw [TRACK] entries
          </h2>
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-gray-50 text-gray-600 text-left">
                <th className="p-2 border border-gray-200 font-medium w-40">
                  Date / Time
                </th>
                <th className="p-2 border border-gray-200 font-medium">
                  Message
                </th>
              </tr>
            </thead>
            <tbody>
              {rawEntries.map((e, i) => (
                <tr key={i} className="even:bg-gray-50">
                  <td className="p-2 border border-gray-200 text-gray-400 whitespace-nowrap">
                    {e.datetime}
                  </td>
                  <td className="p-2 border border-gray-200 font-mono text-xs">
                    {e.message}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
