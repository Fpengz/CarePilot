"use client";

import { Badge } from "@/components/ui/badge";
import { Activity, Zap, Info } from "lucide-react";

interface ClinicalSummaryProps {
  adherence: number;
  risk: number;
  nutrition: number;
  recommendation?: string | {
    title: string;
    detail: string;
  };
}

export function ClinicalSummary({
  adherence,
  risk,
  recommendation,
}: ClinicalSummaryProps) {
  const recTitle = typeof recommendation === "object" ? recommendation.title : "Clinical Insight";
  const recDetail = typeof recommendation === "object" ? recommendation.detail : recommendation;

  return (
    <section className="py-2 space-y-10">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-8 px-2">
        <div className="space-y-4">
          <p className="text-micro-label text-accent-teal uppercase">Primary Health Signal</p>
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
                +4.2% from previous 7d average
              </p>
            </div>
          </div>
        </div>

        <div className="hidden lg:block h-16 w-px bg-border-soft" />

        <div className="space-y-4">
          <p className="text-micro-label text-amber-600 uppercase">Glycemic Risk Profile</p>
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
                Well within target clinical range
              </p>
            </div>
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
