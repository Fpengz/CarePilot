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
    <div className="section-stack max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pb-12 bg-[color:var(--background)] min-h-screen">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between py-6">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-extrabold tracking-tight text-[color:var(--foreground)]">Companion Workspace</h1>
            {active?.engagement.risk_level && (
              <Badge 
                variant="outline"
                className={cn(
                  "rounded-full px-3 py-0.5 text-[10px] font-bold uppercase tracking-widest border shadow-sm",
                  active.engagement.risk_level === "high" 
                    ? "bg-health-rose-soft text-health-rose border-health-rose/20"
                    : active.engagement.risk_level === "medium"
                    ? "bg-health-amber-soft text-health-amber border-health-amber/20"
                    : "bg-health-teal-soft text-health-teal border-health-teal/20"
                )}
              >
                {active.engagement.risk_level} Risk
              </Badge>
            )}
          </div>
          <p className="text-xs text-[color:var(--muted-foreground)] font-medium uppercase tracking-wider">
            Clinical Decision Support & Interaction Orchestration
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={refresh}
            disabled={isRefreshing}
            className="gap-2 rounded-xl h-11 px-4 bg-[color:var(--surface)] shadow-sm border-[color:var(--border-soft)] hover:bg-[color:var(--panel-soft)] transition-all"
            aria-busy={isRefreshing}
          >
            <RefreshCcw className={cn("h-3.5 w-3.5", isRefreshing && "animate-spin")} />
            <AsyncLabel active={isRefreshing} idle="Refresh Workspace" loading="Refreshing" />
          </Button>
        </div>
      </div>

      {error ? (
        <div className="mb-6">
          <ErrorCard message={error} />
        </div>
      ) : null}

      <div className="space-y-8">
        {/* Primary Action */}
        <InteractionForm
          onSuccess={(data) => setInteraction(data)}
          todayData={today ?? undefined}
          isRefreshing={isRefreshing}
          onRefresh={refresh}
        />

        {/* Core Guidance */}
        <div className="grid gap-6 md:grid-cols-2">
          <PatientMedicalCard card={patientCard} showFullLink loading={patientCardLoading} />
          <SupportingEvidenceCard citations={citations} />
        </div>

        {/* Health Signals */}
        <div className="grid gap-6 md:grid-cols-2 pb-12">
          <ImpactWatchCard impact={active?.impact} />
          <BloodPressureCard
            summary={bpSummary ?? active?.snapshot.blood_pressure_summary}
            loading={bpLoading}
            chart={bpChart}
          />
        </div>
      </div>
    </div>
  );
}
