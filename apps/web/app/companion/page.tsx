"use client";

import { useEffect, useState } from "react";
import { RefreshCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ErrorCard } from "@/components/app/error-card";
import { AsyncLabel } from "@/components/app/async-label";
import { cn } from "@/lib/utils";
import {
  getCompanionBloodPressureChart,
  getCompanionBloodPressureSummary,
  getCompanionToday,
  getPatientMedicalCard,
} from "@/lib/api/companion-client";
import type {
  BloodPressureChartApi,
  BloodPressureSummaryApi,
  CompanionInteractionApiResponse,
  CompanionTodayApiResponse,
  PatientMedicalCardApi,
} from "@/lib/types";

import { InteractionForm } from "./components/interaction-form";
import { ImpactWatchCard } from "./components/impact-watch-card";
import { SupportingEvidenceCard } from "./components/supporting-evidence-card";
import { BloodPressureCard } from "./components/blood-pressure-card";
import { PatientMedicalCard } from "./components/patient-medical-card";

export default function CompanionPage() {
  const [today, setToday] = useState<CompanionTodayApiResponse | null>(null);
  const [interaction, setInteraction] = useState<CompanionInteractionApiResponse | null>(null);
  const [patientCard, setPatientCard] = useState<PatientMedicalCardApi | null>(null);
  const [bpSummary, setBpSummary] = useState<BloodPressureSummaryApi | null>(null);
  const [bpChart, setBpChart] = useState<BloodPressureChartApi | null>(null);
  const [bpLoading, setBpLoading] = useState(true);
  const [patientCardLoading, setPatientCardLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  async function refresh() {
    setError(null);
    setIsRefreshing(true);
    setBpLoading(true);
    setPatientCardLoading(true);
    const todayPromise = getCompanionToday();
    const bpPromise = getCompanionBloodPressureSummary();
    const bpChartPromise = getCompanionBloodPressureChart({ range: "30d" });
    const cardPromise = getPatientMedicalCard();
    try {
      const todayResp = await todayPromise;
      setToday(todayResp);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsRefreshing(false);
    }
    void bpPromise
      .then((resp) => setBpSummary(resp.summary ?? null))
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setBpLoading(false));
    void bpChartPromise
      .then((resp) => setBpChart(resp))
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
    void cardPromise
      .then((resp) => setPatientCard(resp))
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setPatientCardLoading(false));
  }

  useEffect(() => {
    void refresh();
  }, []);

  const active = interaction ?? today;
  const activePlan = active?.care_plan;
  const citations = activePlan?.citations ?? [];

  return (
    <div className="section-stack max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pb-12 bg-background min-h-screen relative isolate">
      <div className="dashboard-grounding" />
      
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between py-10 relative z-10">
        <div className="space-y-2">
          <div className="flex items-center gap-4">
            <h1 className="text-h1 font-display tracking-tight text-foreground">Companion Workspace</h1>
            {active?.engagement.risk_level && (
              <Badge 
                variant="outline"
                className={cn(
                  "rounded-full px-4 py-1 text-micro-label font-bold uppercase tracking-widest border shadow-sm",
                  active.engagement.risk_level === "high" 
                    ? "bg-rose-50 text-rose-600 border-rose-200"
                    : active.engagement.risk_level === "medium"
                    ? "bg-amber-50 text-amber-600 border-amber-200"
                    : "bg-accent-teal-muted text-accent-teal border-accent-teal/20"
                )}
              >
                {active.engagement.risk_level} Clinical Risk
              </Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground font-medium max-w-2xl">
            Synthesizing longitudinal health data into actionable clinical reasoning and personalized check-ins.
          </p>
        </div>
        <div className="flex items-center gap-3 pb-1">
          <Button
            variant="secondary"
            size="sm"
            onClick={refresh}
            disabled={isRefreshing}
            className="gap-2 rounded-xl h-11 px-6 bg-surface shadow-sm border-border-soft hover:bg-panel transition-all"
            aria-busy={isRefreshing}
          >
            <RefreshCcw className={cn("h-4 w-4 text-accent-teal", isRefreshing && "animate-spin")} />
            <AsyncLabel active={isRefreshing} idle="Synchronize" loading="Syncing" />
          </Button>
        </div>
      </div>

      {error ? (
        <div className="mb-8 relative z-10">
          <ErrorCard message={error} />
        </div>
      ) : null}

      <div className="space-y-12 relative z-10">
        {/* Primary Interaction Area */}
        <section className="bg-panel border border-border-soft rounded-[2rem] p-1 shadow-sm overflow-hidden">
          <InteractionForm
            onSuccess={(data) => setInteraction(data)}
            todayData={today ?? undefined}
            isRefreshing={isRefreshing}
            onRefresh={refresh}
          />
        </section>

        {/* Intelligence Layers */}
        <div className="grid gap-8 lg:grid-cols-2">
          <div className="space-y-4">
            <div className="px-2">
              <h2 className="text-h2 font-display text-foreground tracking-tight">Clinical Foundation</h2>
              <p className="text-sm text-muted-foreground">Consolidated medical profile and longitudinal reasoning</p>
            </div>
            <PatientMedicalCard card={patientCard} showFullLink loading={patientCardLoading} />
          </div>
          
          <div className="space-y-4">
            <div className="px-2">
              <h2 className="text-h2 font-display text-foreground tracking-tight">Evidence Support</h2>
              <p className="text-sm text-muted-foreground">Peer-reviewed citations and clinical reference sources</p>
            </div>
            <SupportingEvidenceCard citations={citations} />
          </div>
        </div>

        {/* Secondary Signals */}
        <div className="space-y-6">
          <div className="px-2 border-t border-border-soft pt-10">
            <h2 className="text-h2 font-display text-foreground tracking-tight">Vitals & Impact</h2>
            <p className="text-sm text-muted-foreground">Measuring intervention effectiveness across clinical markers</p>
          </div>
          <div className="grid gap-8 lg:grid-cols-2 pb-12">
            <ImpactWatchCard impact={active?.impact} />
            <BloodPressureCard
              summary={bpSummary ?? active?.snapshot.blood_pressure_summary}
              loading={bpLoading}
              chart={bpChart}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
