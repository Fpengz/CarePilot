"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pill, History } from "lucide-react";

import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { Button } from "@/components/ui/button";
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
    <div className="section-stack relative isolate">
      <div className="dashboard-grounding" />
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Care Plan Adherence</h1>
        <p className="text-[color:var(--muted-foreground)] leading-relaxed max-w-2xl text-sm">
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

      <div className="grid grid-cols-12 gap-6 items-start">
        <div className="col-span-12 lg:col-span-8 space-y-8">
          <MedicationIntakeWizard 
            onTextIntake={(text) => intakeTextMutation.mutate(text)}
            onFileUpload={(file) => intakeUploadMutation.mutate(file)}
            busy={intakeTextMutation.isPending || intakeUploadMutation.isPending}
          />

          {intakeResult && (
            <div className="glass-card border-health-teal/20 animate-in zoom-in-95">
              <div className="mb-4">
                <h3 className="text-base font-bold">Normalization Review</h3>
                <p className="text-xs text-[color:var(--muted-foreground)]">Verify the AI-parsed instructions before confirming.</p>
              </div>
              <div className="space-y-4">
                <div className="space-y-3">
                  {intakeResult.normalized_instructions.map((instruction, index) => (
                    <div key={index} className="rounded-xl border border-[color:var(--border-soft)] bg-white/20 dark:bg-black/20 p-4">
                      <div className="font-bold">{instruction.medication_name_raw}</div>
                      <div className="mt-1 text-sm text-[color:var(--muted-foreground)]">
                        {instruction.dosage_text} · {instruction.timing_type} {instruction.fixed_time ? `at ${instruction.fixed_time}` : ""}
                      </div>
                      {instruction.ambiguities.length > 0 && (
                        <div className="mt-2 rounded-lg bg-health-amber-soft p-2 text-[10px] text-health-amber font-medium">
                          ⚠ {instruction.ambiguities.join(" ")}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Button 
                    className="flex-1 rounded-xl h-11"
                    disabled={confirmIntakeMutation.isPending}
                    onClick={() => confirmIntakeMutation.mutate({ draft_id: intakeResult.draft_id })}
                  >
                    Confirm & Create Reminders
                  </Button>
                  <Button variant="secondary" className="rounded-xl h-11" onClick={() => setIntakeResult(null)}>Discard</Button>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Pill className="h-4 w-4 text-[color:var(--muted-foreground)]" />
              <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-[color:var(--muted-foreground)]">Active Regimens</h4>
            </div>
            <div className="grid gap-3">
              {regimens.map((regimen) => (
                <div key={regimen.id} className="glass-card !p-4 group" aria-label={`Regimen for ${regimen.medication_name}`}>
                  <div className="flex items-center justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="font-bold tracking-tight">{regimen.medication_name}</div>
                      <div className="text-xs text-[color:var(--muted-foreground)] mt-0.5">{regimen.dosage_text}</div>
                      <div className="mt-2 flex items-center gap-2">
                        <span className="status-chip status-chip-slate">
                          {regimen.timing_type} {regimen.fixed_time ? `• ${regimen.fixed_time}` : ""}
                        </span>
                        {!regimen.active && <span className="status-chip status-chip-rose">Paused</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        className="rounded-lg"
                        onClick={() => updateRegimenMutation.mutate({ regimenId: regimen.id, active: !regimen.active })}
                      >
                        {regimen.active ? "Pause" : "Resume"}
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
              {regimens.length === 0 && !regimensLoading && (
                <div className="glass-card py-12 text-center">
                  <p className="text-xs text-[color:var(--muted-foreground)] opacity-60">No active regimens found.</p>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="col-span-12 lg:col-span-4 space-y-8 lg:sticky lg:top-28">
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <History className="h-4 w-4 text-[color:var(--muted-foreground)]" />
              <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-[color:var(--muted-foreground)]">Recent Events</h4>
            </div>
            <div className="grid gap-3">
              {adherenceEvents.slice(0, 8).map((event) => (
                <div key={event.id} className="glass-card !p-3">
                  <div className="flex items-center justify-between">
                    <span className={cn(
                      "status-chip",
                      event.status === "taken" ? "status-chip-teal" : "status-chip-rose"
                    )}>
                      {event.status}
                    </span>
                    <span className="text-[10px] font-medium text-[color:var(--muted-foreground)]">
                      {new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "numeric" }).format(new Date(event.scheduled_at))}
                    </span>
                  </div>
                  <div className="mt-2 text-xs font-bold truncate">
                    {regimens.find(r => r.id === event.regimen_id)?.medication_name ?? "Medication"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
