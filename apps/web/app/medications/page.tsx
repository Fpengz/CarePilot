"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pill, History } from "lucide-react";

import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  cancelMedicationDraft,
  confirmMedicationIntake,
  deleteMedicationDraftInstruction,
  deleteMedicationRegimen,
  getMedicationAdherenceMetrics,
  intakeMedicationFromText,
  intakeMedicationFromUpload,
  listMedicationRegimens,
  updateMedicationDraftInstruction,
  updateMedicationRegimen,
} from "@/lib/api/medication-client";
import type {
  MedicationIntakeApiResponse,
  MedicationRegimenApi,
} from "@/lib/types";
import { MedicationMetricsSummary } from "./components/medication-metrics-summary";
import { MedicationIntakeWizard } from "./components/medication-intake-wizard";
import { cn } from "@/lib/utils";

export default function MedicationsPage() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [intakeResult, setIntakeResult] = useState<MedicationIntakeApiResponse | null>(null);

  const { data: regimensResult, isLoading: regimensLoading } = useQuery({
    queryKey: ["medication-regimens"],
    queryFn: listMedicationRegimens,
  });
  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ["medication-metrics"],
    queryFn: () => getMedicationAdherenceMetrics(),
  });

  const intakeTextMutation = useMutation({
    mutationFn: (text: string) => intakeMedicationFromText({ instructions_text: text }),
    onSuccess: (result) => {
      setIntakeResult(result);
      setError(null);
    },
    onError: (mutationError) => {
      setError(mutationError instanceof Error ? mutationError.message : String(mutationError));
    },
  });

  const intakeUploadMutation = useMutation({
    mutationFn: (file: File) => intakeMedicationFromUpload(file),
    onSuccess: (result) => {
      setIntakeResult(result);
      setError(null);
    },
    onError: (mutationError) => {
      setError(mutationError instanceof Error ? mutationError.message : String(mutationError));
    },
  });

  const confirmIntakeMutation = useMutation({
    mutationFn: confirmMedicationIntake,
    onSuccess: async (result) => {
      setIntakeResult(null);
      setError(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["medication-regimens"] }),
        queryClient.invalidateQueries({ queryKey: ["medication-metrics"] }),
      ]);
    },
  });

  const updateRegimenMutation = useMutation({
    mutationFn: ({ regimenId, active }: { regimenId: string; active: boolean }) =>
      updateMedicationRegimen(regimenId, { active }),
    onSuccess: async () => {
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["medication-regimens"] });
    },
  });

  const deleteRegimenMutation = useMutation({
    mutationFn: deleteMedicationRegimen,
    onSuccess: async () => {
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["medication-regimens"] });
    },
  });

  const regimens = regimensResult?.items ?? [];
  const adherenceEvents = metrics?.events ?? [];
  const busy =
    intakeTextMutation.isPending ||
    intakeUploadMutation.isPending ||
    confirmIntakeMutation.isPending ||
    regimensLoading ||
    metricsLoading;

  return (
    <div className="section-stack max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pb-12 bg-background min-h-screen relative isolate">
      <div className="dashboard-grounding" />
      <div className="flex flex-col gap-2 py-10">
        <h1 className="text-h1 font-display tracking-tight text-foreground">Care Plan Adherence</h1>
        <p className="text-muted-foreground leading-relaxed max-w-2xl text-sm font-medium">
          Track medication follow-through, normalize complex prescriptions using AI, and manage your clinical regimens.
        </p>
      </div>

      <MedicationMetricsSummary 
        adherenceRate={metrics?.totals?.adherence_rate ? metrics.totals.adherence_rate * 100 : 0}
        totalEvents={metrics?.totals?.events ?? 0}
        taken={metrics?.totals?.taken ?? 0}
        missed={metrics?.totals?.missed ?? 0}
        loading={metricsLoading}
      />

      {error && <ErrorCard message={error} />}

      <div className="grid grid-cols-12 gap-12 items-start mt-8">
        <div className="col-span-12 lg:col-span-8 space-y-12">
          <MedicationIntakeWizard 
            onTextIntake={(text) => intakeTextMutation.mutate(text)}
            onFileUpload={(file) => intakeUploadMutation.mutate(file)}
            busy={intakeTextMutation.isPending || intakeUploadMutation.isPending}
          />

          {intakeResult && (
            <div className="bg-panel border border-accent-teal/20 rounded-3xl p-8 shadow-sm animate-in zoom-in-95">
              <div className="mb-6">
                <h3 className="text-xl font-semibold tracking-tight text-foreground">Normalization Review</h3>
                <p className="text-sm text-muted-foreground font-medium">Verify the clinical reasoning before finalizing reminders.</p>
              </div>
              <div className="space-y-6">
                <div className="space-y-4">
                  {intakeResult.normalized_instructions.map((instruction, index) => (
                    <div key={index} className="rounded-2xl border border-border-soft bg-surface p-5 shadow-sm">
                      <div className="font-bold text-foreground">{instruction.medication_name_raw}</div>
                      <div className="mt-1 text-sm text-muted-foreground">
                        {instruction.dosage_text} · {instruction.timing_type} {instruction.fixed_time ? `at ${instruction.fixed_time}` : ""}
                      </div>
                      {instruction.ambiguities.length > 0 && (
                        <div className="mt-3 rounded-xl bg-amber-50 border border-amber-100 p-3 text-[11px] text-amber-700 font-bold">
                          ⚠ {instruction.ambiguities.join(" ")}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                <div className="flex gap-3">
                  <Button 
                    className="flex-1 rounded-xl h-12 font-bold shadow-lg shadow-accent-teal/20"
                    disabled={confirmIntakeMutation.isPending}
                    onClick={() => confirmIntakeMutation.mutate({ draft_id: intakeResult.draft_id })}
                  >
                    Confirm & Create Reminders
                  </Button>
                  <Button variant="secondary" className="rounded-xl h-12 px-8 font-semibold" onClick={() => setIntakeResult(null)}>Discard</Button>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-6">
            <div className="flex items-center gap-2 px-1">
              <Pill className="h-4 w-4 text-accent-teal" />
              <h4 className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground">Active Clinical Regimens</h4>
            </div>
            <div className="grid gap-4">
              {regimens.map((regimen) => (
                <div key={regimen.id} className="bg-panel border border-border-soft rounded-2xl p-5 shadow-sm group hover:border-accent-teal/30 transition-all" aria-label={`Regimen for ${regimen.medication_name}`}>
                  <div className="flex items-center justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="font-bold tracking-tight text-foreground">{regimen.medication_name}</div>
                      <div className="text-xs text-muted-foreground mt-0.5 font-medium">{regimen.dosage_text}</div>
                      <div className="mt-3 flex items-center gap-2">
                        <Badge variant="outline" className="bg-surface text-micro-label font-bold border-border-soft px-3">
                          {regimen.timing_type} {regimen.fixed_time ? `• ${regimen.fixed_time}` : ""}
                        </Badge>
                        {!regimen.active && <Badge variant="outline" className="bg-rose-50 text-rose-600 border-rose-100 text-micro-label font-bold px-3">Paused</Badge>}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        className="rounded-lg h-9 px-4 text-xs"
                        onClick={() => updateRegimenMutation.mutate({ regimenId: regimen.id, active: !regimen.active })}
                      >
                        {regimen.active ? "Pause" : "Resume"}
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
              {regimens.length === 0 && !regimensLoading && (
                <div className="bg-panel border border-dashed border-border-soft rounded-3xl py-16 text-center">
                  <p className="text-sm text-muted-foreground font-medium italic opacity-60">No active regimens observed.</p>
                </div>
              )}
            </div>
          </div>
        </div>

        <aside className="col-span-12 lg:col-span-4 space-y-10 lg:sticky lg:top-28">
          <div className="space-y-6">
            <div className="flex items-center gap-2 px-1">
              <History className="h-4 w-4 text-accent-teal" />
              <h4 className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground">Longitudinal Adherence</h4>
            </div>
            <div className="grid gap-3">
              {adherenceEvents.slice(0, 8).map((event) => (
                <div key={event.id} className="bg-panel border border-border-soft rounded-2xl p-4 shadow-sm">
                  <div className="flex items-center justify-between">
                    <Badge variant="outline" className={cn(
                      "text-[10px] font-bold uppercase tracking-widest px-2",
                      event.status === "taken" ? "bg-emerald-50 text-emerald-600 border-emerald-100" : "bg-rose-50 text-rose-600 border-rose-100"
                    )}>
                      {event.status}
                    </Badge>
                    <span className="text-[10px] font-bold text-muted-foreground uppercase">
                      {new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "numeric" }).format(new Date(event.scheduled_at))}
                    </span>
                  </div>
                  <div className="mt-3 text-sm font-bold text-foreground truncate">
                    {regimens.find(r => r.id === event.regimen_id)?.medication_name ?? "Clinical Dosage"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
