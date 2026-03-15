"use client";

import { useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, Label } from "recharts";
import { DashboardMacroChartApi } from "@/lib/types";
import { CHART_COLORS, COMMON_AXIS_PROPS, ClinicalTooltip } from "./chart-utils";
import { cn } from "@/lib/utils";

type ViewMode = "all" | "protein" | "carbs" | "fat";

export function NutritionBalanceChart({ chart }: { chart: DashboardMacroChartApi }) {
  const [view, setView] = useState<ViewMode>("all");
  const data = chart.points;

  const modes: { id: ViewMode; label: string; color: string }[] = [
    { id: "all", label: "All", color: "var(--foreground)" },
    { id: "protein", label: "Protein", color: CHART_COLORS.protein },
    { id: "carbs", label: "Carbs", color: CHART_COLORS.carbs },
    { id: "fat", label: "Fat", color: CHART_COLORS.fat },
  ];

  return (
    <div className="glass-card h-full">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between mb-6">
        <div className="flex flex-col items-start gap-1">
          <span className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Nutrient Profile</span>
          <h3 className="text-lg font-bold tracking-tight">{chart.title}</h3>
        </div>
        <div className="flex bg-black/5 dark:bg-white/5 p-1 rounded-lg self-start">
          {modes.map((m) => (
            <button
              key={m.id}
              onClick={() => setView(m.id)}
              className={cn(
                "px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all",
                view === m.id ? "bg-white dark:bg-black shadow-sm text-[color:var(--foreground)]" : "text-[color:var(--muted-foreground)] hover:text-[color:var(--foreground)]"
              )}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 0, right: 0, left: 10, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--chart-grid)" strokeOpacity={0.5} />
            <XAxis dataKey="label" {...COMMON_AXIS_PROPS} tickMargin={10} />
            <YAxis {...COMMON_AXIS_PROPS} width={40}>
              <Label 
                value="GRAMS (G)" 
                angle={-90} 
                position="insideLeft" 
                style={{ textAnchor: 'middle', fontSize: '8px', fontWeight: 'bold', fill: 'var(--chart-text)', opacity: 0.8 }} 
              />
            </YAxis>
            <Tooltip content={<ClinicalTooltip />} cursor={{ fill: "var(--chart-grid)", fillOpacity: 0.1 }} />
            
            {(view === "all" || view === "protein") && (
              <Bar dataKey="protein_g" name="Protein" fill={CHART_COLORS.protein} stackId="a" radius={view === "protein" ? [4, 4, 0, 0] : [0, 0, 0, 0]} />
            )}
            {(view === "all" || view === "carbs") && (
              <Bar dataKey="carbs_g" name="Carbs" fill={CHART_COLORS.carbs} stackId="a" radius={view === "carbs" ? [4, 4, 0, 0] : [0, 0, 0, 0]} />
            )}
            {(view === "all" || view === "fat") && (
              <Bar dataKey="fat_g" name="Fat" fill={CHART_COLORS.fat} stackId="a" radius={[4, 4, 0, 0]} />
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
