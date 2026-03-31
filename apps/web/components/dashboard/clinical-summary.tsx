"use client";

import { Badge } from "@/components/ui/badge";
import { Activity, Zap, Info } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";

interface ClinicalSummaryProps {
  adherence: number;
  risk: number;
  nutrition: number;
  adherenceChart?: any[];
  riskChart?: any[];
  recommendation?: string | {
    title: string;
    detail: string;
  };
}

export function ClinicalSummary({
  adherence,
  risk,
  nutrition,
  adherenceChart = [],
  riskChart = [],
  recommendation,
}: ClinicalSummaryProps) {
  const recTitle = typeof recommendation === "object" ? recommendation.title : "Clinical Insight";
  const recDetail = typeof recommendation === "object" ? recommendation.detail : recommendation;

  return (
    <section className="py-2 space-y-10">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-12 px-2">
        <div className="flex-1 space-y-6">
          <div className="space-y-4">
            <p className="text-micro-label text-accent-teal uppercase font-bold tracking-widest">Metabolic Adherence</p>
            <div className="flex items-baseline gap-4">
              <h2 className="text-6xl font-bold tracking-tighter text-foreground">
                {Math.round(adherence)}<span className="text-3xl text-muted-foreground ml-1">%</span>
              </h2>
              <div className="space-y-1">
                <Badge className="bg-accent-teal/10 text-accent-teal border-accent-teal/20 px-3 py-1 text-[11px] font-bold">
                  <Activity className="h-3 w-3 mr-1.5" />
                  METABOLIC: STABLE
                </Badge>
                <p className="text-xs text-muted-foreground font-medium pl-1">
                  +4.2% vs previous period
                </p>
              </div>
            </div>
          </div>
          <div className="h-12 w-full max-w-sm opacity-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={adherenceChart}>
                <Area type="monotone" dataKey="value" stroke="var(--accent-teal)" fill="var(--accent-teal)" fillOpacity={0.1} strokeWidth={3} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="hidden lg:block h-24 w-px bg-border-soft self-center" />

        <div className="flex-1 space-y-6">
          <div className="space-y-4">
            <p className="text-micro-label text-amber-600 uppercase font-bold tracking-widest">Glycemic Risk Profile</p>
            <div className="flex items-baseline gap-4">
              <h2 className="text-6xl font-bold tracking-tighter text-foreground">
                {Math.round(risk)}<span className="text-3xl text-muted-foreground ml-1">/100</span>
              </h2>
              <div className="space-y-1">
                <Badge className="bg-amber-50 text-amber-600 border-amber-200 px-3 py-1 text-[11px] font-bold">
                  <Zap className="h-3 w-3 mr-1.5" />
                  RISK: LOW
                </Badge>
                <p className="text-xs text-muted-foreground font-medium pl-1">
                  Stable clinical trajectory
                </p>
              </div>
            </div>
          </div>
          <div className="h-12 w-full max-w-sm opacity-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={riskChart}>
                <Area type="monotone" dataKey="value" stroke="#d97706" fill="#d97706" fillOpacity={0.1} strokeWidth={3} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="bg-panel rounded-3xl p-8 border border-border-soft flex items-start gap-6 shadow-sm">
        <div className="h-12 w-12 rounded-2xl bg-white shadow-sm border border-border-soft flex items-center justify-center shrink-0">
          <Info className="h-6 w-6 text-accent-teal" />
        </div>
        <div className="space-y-2">
          <h3 className="text-xl font-semibold tracking-tight text-foreground">
            {recTitle || "Clinical Insight"}
          </h3>
          <p className="text-muted-foreground leading-relaxed text-sm">
            {recDetail || "Continue maintaining your current meal rhythm. Your glycemic stability is showing consistent improvement week-over-week."}
          </p>
        </div>
      </div>
    </section>
  );
}
