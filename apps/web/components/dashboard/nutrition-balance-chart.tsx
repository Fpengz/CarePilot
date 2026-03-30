"use client";

import { useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, Label, Legend } from "recharts";
import { DashboardMacroChartApi } from "@/lib/types";
import { CHART_COLORS, COMMON_AXIS_PROPS, ClinicalTooltip } from "./chart-utils";
import { cn } from "@/lib/utils";

type ViewMode = "all" | "protein" | "carbs" | "fat";

const FUEL_COLORS = {
  carbs: "#00a6ed",   // Warm Cream
  protein: "#f6511d", // Soft Clay
  fat: "#ffb400",     // Soft Sky
};

export function NutritionBalanceChart({ chart }: { chart: DashboardMacroChartApi }) {
  const [view, setView] = useState<ViewMode>("all");
  const data = chart.points;

  const modes: { id: ViewMode; label: string; color: string }[] = [
    { id: "all", label: "All", color: "var(--foreground)" },
    { id: "protein", label: "Protein", color: FUEL_COLORS.protein },
    { id: "carbs", label: "Carbs", color: FUEL_COLORS.carbs },
    { id: "fat", label: "Fat", color: FUEL_COLORS.fat },
  ];

  return (
    <div className="bg-panel border border-border-soft rounded-3xl p-8 shadow-sm h-full">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between mb-8 px-1">
        <div className="flex flex-col items-start gap-1">
          <span className="text-micro-label text-muted-foreground uppercase">Nutrient Profile</span>
          <h3 className="text-xl font-semibold tracking-tight text-foreground">{chart.title}</h3>
        </div>
        <div className="flex bg-surface border border-border-soft p-1 rounded-xl self-start shadow-sm">
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
          <BarChart data={data} margin={{ top: 0, right: 0, left: 10, bottom: 20 }}>
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
            <Legend 
              verticalAlign="bottom" 
              align="center" 
              content={({ payload }) => (
                <div className="flex justify-center gap-6 mt-4">
                  {payload?.map((entry: any, index: number) => (
                    <div key={`item-${index}`} className="flex items-center gap-2">
                      <div className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.color }} />
                      <span className="text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)]">
                        {entry.value}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            />
            
            {(view === "all" || view === "protein") && (
              <Bar 
                dataKey="protein_g" 
                name="Protein" 
                fill={FUEL_COLORS.protein} 
                fillOpacity={0.9}
                stackId="a" 
                radius={view === "protein" ? [4, 4, 0, 0] : [0, 0, 0, 0]} 
              />
            )}
            {(view === "all" || view === "carbs") && (
              <Bar 
                dataKey="carbs_g" 
                name="Carbs" 
                fill={FUEL_COLORS.carbs} 
                fillOpacity={0.9}
                stackId="a" 
                radius={view === "carbs" ? [4, 4, 0, 0] : [0, 0, 0, 0]} 
              />
            )}
            {(view === "all" || view === "fat") && (
              <Bar 
                dataKey="fat_g" 
                name="Fat" 
                fill={FUEL_COLORS.fat} 
                fillOpacity={0.9}
                stackId="a" 
                radius={[4, 4, 0, 0]} 
              />
            )}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
