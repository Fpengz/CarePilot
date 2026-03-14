"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  confirmMedicationIntake,
  deleteMedicationRegimen,
  getMedicationAdherenceMetrics,
  intakeMedicationFromText,
  intakeMedicationFromUpload,
  listMedicationRegimens,
  updateMedicationRegimen,
} from "@/lib/api/medication-client";
import type {
  MedicationIntakeApiResponse,
  MedicationRegimenApi,
} from "@/lib/types";

export default function MedicationsPage() {
  const queryClient = useQueryClient();
  const [instructionsText, setInstructionsText] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
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
    mutationFn: intakeMedicationFromText,
    onSuccess: async (result) => {
      setIntakeResult(result);
      setError(null);
      setSelectedFile(null);
    },
    onError: (mutationError) => {
      setError(mutationError instanceof Error ? mutationError.message : String(mutationError));
    },
  });

  const intakeUploadMutation = useMutation({
    mutationFn: intakeMedicationFromUpload,
    onSuccess: async (result) => {
      setIntakeResult(result);
      setError(null);
      setInstructionsText("");
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
    onError: (mutationError) => {
      setError(mutationError instanceof Error ? mutationError.message : String(mutationError));
    },
  });

  const updateRegimenMutation = useMutation({
    mutationFn: ({ regimenId, active }: { regimenId: string; active: boolean }) =>
      updateMedicationRegimen(regimenId, { active }),
    onSuccess: async () => {
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["medication-regimens"] });
    },
    onError: (mutationError) => {
      setError(mutationError instanceof Error ? mutationError.message : String(mutationError));
    },
  });

  const deleteRegimenMutation = useMutation({
    mutationFn: deleteMedicationRegimen,
    onSuccess: async () => {
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["medication-regimens"] });
    },
    onError: (mutationError) => {
      setError(mutationError instanceof Error ? mutationError.message : String(mutationError));
    },
  });

  const regimens = regimensResult?.items ?? [];
  const adherenceEvents = metrics?.events ?? [];
  const busy =
    intakeTextMutation.isPending ||
    intakeUploadMutation.isPending ||
    confirmIntakeMutation.isPending ||
    updateRegimenMutation.isPending ||
    deleteRegimenMutation.isPending;

  return (
    <div>
      <PageTitle
        eyebrow="Care"
        title="Medications & Adherence"
        description="Paste medication instructions or upload a prescription, review the normalized regimen draft, and keep reminders active."
        tags={["medication intake", "adherence", "reminders"]}
      />

      <div className="page-grid">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Adherence Metrics</CardTitle>
              <CardDescription>Your current medication follow-through.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Adherence Rate</div>
                  <div className="mt-1 text-sm font-medium">
                    {metricsLoading ? "Loading…" : metrics?.totals ? `${Math.round(metrics.totals.adherence_rate * 100)}%` : "—"}
                  </div>
                </div>
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Events</div>
                  <div className="mt-1 text-sm font-medium">{metricsLoading ? "Loading…" : metrics?.totals?.events ?? 0}</div>
                </div>
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Taken</div>
                  <div className="mt-1 text-sm font-medium">{metricsLoading ? "Loading…" : metrics?.totals?.taken ?? 0}</div>
                </div>
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Skipped/Missed</div>
                  <div className="mt-1 text-sm font-medium">
                    {metricsLoading ? "Loading…" : (metrics?.totals?.skipped ?? 0) + (metrics?.totals?.missed ?? 0)}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Medication Intake</CardTitle>
              <CardDescription>Use common prescription wording like “Take Metformin 500mg twice daily before meals”.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {error ? <ErrorCard message={error} /> : null}

              <div className="space-y-2">
                <Label htmlFor="medication-instructions">Pasted Instructions</Label>
                <Textarea
                  id="medication-instructions"
                  value={instructionsText}
                  onChange={(event) => setInstructionsText(event.target.value)}
                  placeholder="Paracetamol 500mg, three times a day after meals for 5 days"
                  rows={5}
                />
              </div>

              <div className="flex flex-wrap gap-2">
                <Button
                  disabled={busy || !instructionsText.trim()}
                  onClick={() => intakeTextMutation.mutate({ instructions_text: instructionsText.trim() })}
                >
                  {intakeTextMutation.isPending ? "Parsing…" : "Preview From Text"}
                </Button>
              </div>

              <div className="space-y-2 border-t border-[color:var(--border)] pt-4">
                <Label htmlFor="medication-upload">Upload Prescription</Label>
                <Input
                  id="medication-upload"
                  type="file"
                  accept=".pdf,.txt,image/*"
                  onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                />
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="secondary"
                    disabled={busy || !selectedFile}
                    onClick={() => {
                      if (selectedFile) intakeUploadMutation.mutate(selectedFile);
                    }}
                  >
                    {intakeUploadMutation.isPending ? "Uploading…" : "Upload & Preview"}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Latest Intake Draft</CardTitle>
              <CardDescription>Review the normalized instructions and the reminders created for today.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {intakeResult ? (
                <>
                  <div className="rounded-xl border border-[color:var(--border)] p-3 text-sm">
                    <div className="font-medium">{intakeResult.source.source_type === "upload" ? intakeResult.source.filename ?? "Uploaded file" : "Pasted text"}</div>
                    <div className="mt-1 text-xs text-[color:var(--muted-foreground)] break-all">source hash: {intakeResult.source.source_hash}</div>
                    <div className="mt-2 text-sm text-[color:var(--muted-foreground)]">{intakeResult.source.extracted_text}</div>
                  </div>

                  <div className="space-y-3">
                    {intakeResult.normalized_instructions.map((instruction, index) => (
                      <div key={`${instruction.medication_name_raw}-${index}`} className="rounded-xl border border-[color:var(--border)] p-3">
                        <div className="font-medium">{instruction.medication_name_raw} {instruction.dosage_text}</div>
                        <div className="mt-1 text-xs text-[color:var(--muted-foreground)]">
                          {instruction.timing_type} • {instruction.frequency_times_per_day} dose(s)/day
                          {instruction.fixed_time ? ` • ${instruction.fixed_time}` : ""}
                        </div>
                        {instruction.ambiguities.length > 0 ? (
                          <div className="mt-2 text-xs text-amber-700 dark:text-amber-300">{instruction.ambiguities.join(" ")}</div>
                        ) : null}
                      </div>
                    ))}
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Regimens Created</div>
                      <div className="mt-1 text-sm font-medium">{intakeResult.regimens.length}</div>
                    </div>
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Today’s Reminders</div>
                      <div className="mt-1 text-sm font-medium">{intakeResult.reminders.length}</div>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Button
                      disabled={
                        busy ||
                        intakeResult.normalized_instructions.length === 0 ||
                        intakeResult.regimens.length > 0
                      }
                      onClick={() => confirmIntakeMutation.mutate({ draft_id: intakeResult.draft_id })}
                    >
                      {confirmIntakeMutation.isPending ? "Confirming…" : "Confirm Draft & Create Reminders"}
                    </Button>
                  </div>
                </>
              ) : (
                <p className="text-sm text-[color:var(--muted-foreground)]">No intake result yet. Submit text or upload a prescription to review the normalized draft.</p>
              )}
            </CardContent>
          </Card>
        </div>

        <Tabs defaultValue="regimens" className="w-full">
          <TabsList className="mb-4">
            <TabsTrigger value="regimens">Regimens</TabsTrigger>
            <TabsTrigger value="history">Adherence History</TabsTrigger>
          </TabsList>

          <TabsContent value="regimens" className="space-y-4 mt-0">
            {regimensLoading ? <p className="text-sm text-[color:var(--muted-foreground)]">Loading regimens…</p> : null}
            {regimens.map((regimen: MedicationRegimenApi) => (
              <Card key={regimen.id}>
                <CardContent className="pt-6 space-y-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="font-medium">{regimen.medication_name}</div>
                      <div className="text-sm text-[color:var(--muted-foreground)]">{regimen.dosage_text}</div>
                      <div className="mt-1 text-xs text-[color:var(--muted-foreground)]">
                        {regimen.timing_type}
                        {regimen.fixed_time ? ` • ${regimen.fixed_time}` : ""}
                        {regimen.start_date ? ` • starts ${regimen.start_date}` : ""}
                        {regimen.end_date ? ` • ends ${regimen.end_date}` : ""}
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="secondary"
                        disabled={busy}
                        onClick={() => updateRegimenMutation.mutate({ regimenId: regimen.id, active: !regimen.active })}
                      >
                        {regimen.active ? "Deactivate" : "Activate"}
                      </Button>
                      <Button
                        variant="secondary"
                        disabled={busy}
                        onClick={() => deleteRegimenMutation.mutate(regimen.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                  {regimen.instructions_text ? (
                    <div className="text-xs text-[color:var(--muted-foreground)]">{regimen.instructions_text}</div>
                  ) : null}
                </CardContent>
              </Card>
            ))}
            {!regimensLoading && regimens.length === 0 ? (
              <p className="text-sm text-[color:var(--muted-foreground)]">No medication regimens yet.</p>
            ) : null}
          </TabsContent>

          <TabsContent value="history" className="space-y-4 mt-0">
            {adherenceEvents.length > 0 ? (
              adherenceEvents.map((event) => (
                <Card key={event.id}>
                  <CardContent className="pt-6">
                    <div className="font-medium">{event.status}</div>
                    <div className="mt-1 text-sm text-[color:var(--muted-foreground)]">
                      Scheduled {new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(event.scheduled_at))}
                    </div>
                    <div className="mt-1 text-xs text-[color:var(--muted-foreground)]">
                      source: {event.source} • regimen {event.regimen_id}
                    </div>
                  </CardContent>
                </Card>
              ))
            ) : (
              <p className="text-sm text-[color:var(--muted-foreground)]">No adherence events recorded yet.</p>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
