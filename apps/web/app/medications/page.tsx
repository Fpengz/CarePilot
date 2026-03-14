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
      setIntakeResult(result);
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
    <div className="section-stack">
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

      <div className="page-grid items-start gap-6 lg:gap-8">
        <div className="space-y-8">
          <MedicationIntakeWizard 
            onTextIntake={(text) => intakeTextMutation.mutate(text)}
            onFileUpload={(file) => intakeUploadMutation.mutate(file)}
            busy={intakeTextMutation.isPending || intakeUploadMutation.isPending}
          />

          {intakeResult && (
            <Card className="border-[color:var(--accent)]/20 shadow-sm animate-in zoom-in-95">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Normalization Review</CardTitle>
                <CardDescription>Verify the AI-parsed instructions before confirming.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-3">
                  {intakeResult.normalized_instructions.map((instruction, index) => (
                    <div key={index} className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-4">
                      <div className="font-bold">{instruction.medication_name_raw}</div>
                      <div className="mt-1 text-sm text-[color:var(--muted-foreground)]">
                        {instruction.dosage_text} · {instruction.timing_type} {instruction.fixed_time ? `at ${instruction.fixed_time}` : ""}
                      </div>
                      {instruction.ambiguities.length > 0 && (
                        <div className="mt-2 rounded-lg bg-amber-50 p-2 text-[10px] text-amber-700 font-medium">
                          ⚠ {instruction.ambiguities.join(" ")}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Button 
                    className="flex-1"
                    disabled={confirmIntakeMutation.isPending}
                    onClick={() => confirmIntakeMutation.mutate({ draft_id: intakeResult.draft_id })}
                  >
                    Confirm & Create Reminders
                  </Button>
                  <Button variant="outline" onClick={() => setIntakeResult(null)}>Discard</Button>
                </div>
              </CardContent>
            </Card>
          )}

          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Pill className="h-4 w-4 text-[color:var(--muted-foreground)]" />
              <h4 className="text-xs font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Active Regimens</h4>
            </div>
            <div className="grid gap-3">
              {regimens.map((regimen) => (
                <div key={regimen.id} className="data-list-row group" aria-label={`Regimen for ${regimen.medication_name}`}>
                  <div className="flex items-center justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="font-bold tracking-tight">{regimen.medication_name}</div>
                      <div className="text-xs text-[color:var(--muted-foreground)] mt-0.5">{regimen.dosage_text}</div>
                      <div className="mt-2 text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)] opacity-60">
                        {regimen.timing_type} {regimen.fixed_time ? `• ${regimen.fixed_time}` : ""}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => updateRegimenMutation.mutate({ regimenId: regimen.id, active: !regimen.active })}
                      >
                        {regimen.active ? "Pause" : "Resume"}
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
              {regimens.length === 0 && !regimensLoading && (
                <p className="py-8 text-center text-xs text-[color:var(--muted-foreground)] opacity-60">No active regimens found.</p>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-8 lg:sticky lg:top-28">
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <History className="h-4 w-4 text-[color:var(--muted-foreground)]" />
              <h4 className="text-xs font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Recent Events</h4>
            </div>
            <div className="grid gap-3">
              {adherenceEvents.slice(0, 5).map((event) => (
                <div key={event.id} className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-3 shadow-sm">
                  <div className="flex items-center justify-between">
                    <span className={cn(
                      "rounded-full px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider",
                      event.status === "taken" ? "bg-emerald-500/10 text-emerald-600" : "bg-rose-500/10 text-rose-600"
                    )}>
                      {event.status}
                    </span>
                    <span className="text-[10px] text-[color:var(--muted-foreground)]">
                      {new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "numeric" }).format(new Date(event.scheduled_at))}
                    </span>
                  </div>
                  <div className="mt-1 text-xs font-semibold truncate">{regimens.find(r => r.id === event.regimen_id)?.medication_name ?? "Medication"}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
