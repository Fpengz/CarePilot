"use client";

import { Pill, History } from "lucide-react";

import { ErrorCard } from "@/components/app/error-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MedicationMetricsSummary } from "./components/medication-metrics-summary";
import { MedicationIntakeWizard } from "./components/medication-intake-wizard";
import { cn } from "@/lib/utils";
import { useMedications } from "./hooks/use-medications";

export default function MedicationsPage() {
  const {
    regimens,
    adherenceEvents,
    metrics,
    metricsLoading,
    regimensLoading,
    error,
    intakeResult,
    setIntakeResult,
    intakeText,
    intakeUpload,
    confirmIntake,
    toggleRegimen,
    isPendingIntake,
    isPendingConfirm,
  } = useMedications();

  return (
    <main className="section-stack max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pb-12 bg-background min-h-screen relative isolate">
      <div className="dashboard-grounding" aria-hidden="true" />
      
      <header className="flex flex-col gap-2 py-10">
        <h1 className="text-h1 font-display tracking-tight text-foreground">Care Plan Adherence</h1>
        <p className="text-muted-foreground leading-relaxed max-w-2xl text-sm font-medium">
          Track medication follow-through, normalize complex prescriptions using AI, and manage your clinical regimens.
        </p>
      </header>

      <section aria-label="Medication Metrics">
        <MedicationMetricsSummary 
          adherenceRate={metrics?.totals?.adherence_rate ? metrics.totals.adherence_rate * 100 : 0}
          totalEvents={metrics?.totals?.events ?? 0}
          taken={metrics?.totals?.taken ?? 0}
          missed={metrics?.totals?.missed ?? 0}
          loading={metricsLoading}
        />
      </section>

      {error && (
        <div className="mt-8" role="alert">
          <ErrorCard message={error} />
        </div>
      )}

      <div className="grid grid-cols-12 gap-12 items-start mt-8">
        <div className="col-span-12 lg:col-span-8 space-y-12">
          <section aria-label="Intake Assistant">
            <MedicationIntakeWizard 
              onTextIntake={intakeText}
              onFileUpload={intakeUpload}
              busy={isPendingIntake}
            />
          </section>

          {intakeResult && (
            <section className="bg-panel border border-accent-teal/20 rounded-2xl p-8 shadow-sm animate-in zoom-in-95" aria-labelledby="review-heading">
              <div className="mb-6">
                <h3 id="review-heading" className="text-lg font-semibold tracking-tight text-foreground">Normalization Review</h3>
                <p className="text-sm text-muted-foreground font-medium">Verify the clinical reasoning before finalizing reminders.</p>
              </div>
              <div className="space-y-6">
                <div className="space-y-4">
                  {intakeResult.normalized_instructions.map((instruction, index) => (
                    <article key={index} className="rounded-xl border border-border-soft bg-surface p-5 shadow-sm">
                      <div className="font-bold text-foreground">{instruction.medication_name_raw}</div>
                      <div className="mt-1 text-sm text-muted-foreground">
                        {instruction.dosage_text} · {instruction.timing_type} {instruction.fixed_time ? `at ${instruction.fixed_time}` : ""}
                      </div>
                      {instruction.ambiguities.length > 0 && (
                        <div className="mt-3 rounded-lg bg-health-amber/10 border border-health-amber/20 p-3 text-[11px] text-health-amber font-bold">
                          ⚠ {instruction.ambiguities.join(" ")}
                        </div>
                      )}
                    </article>
                  ))}
                </div>
                <div className="flex gap-3">
                  <Button 
                    className="flex-1 rounded-xl h-11 font-bold shadow-sm"
                    disabled={isPendingConfirm}
                    onClick={() => confirmIntake(intakeResult.draft_id)}
                  >
                    Confirm & Create Reminders
                  </Button>
                  <Button variant="secondary" className="rounded-xl h-11 px-8 font-semibold" onClick={() => setIntakeResult(null)}>Discard</Button>
                </div>
              </div>
            </section>
          )}

          <section className="space-y-6">
            <div className="flex items-center gap-2 px-1">
              <Pill className="h-4 w-4 text-accent-teal" aria-hidden="true" />
              <h4 className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground">Active Clinical Regimens</h4>
            </div>
            <div className="grid gap-3">
              {regimens.map((regimen) => (
                <article key={regimen.id} className="bg-panel border border-border-soft rounded-xl p-5 shadow-sm group hover:border-accent-teal/30 transition-all">
                  <div className="flex items-center justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="font-bold tracking-tight text-foreground">{regimen.medication_name}</div>
                      <div className="text-xs text-muted-foreground mt-0.5 font-medium">{regimen.dosage_text}</div>
                      <div className="mt-3 flex items-center gap-2">
                        <Badge variant="outline" className="bg-surface text-[10px] font-bold border-border-soft px-2.5 py-0.5">
                          {regimen.timing_type} {regimen.fixed_time ? `• ${regimen.fixed_time}` : ""}
                        </Badge>
                        {!regimen.active && (
                          <Badge variant="outline" className="bg-health-rose/10 text-health-rose border-health-rose/20 text-[10px] font-bold px-2.5 py-0.5">
                            Paused
                          </Badge>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        className="rounded-lg h-9 px-4 text-xs font-semibold"
                        onClick={() => toggleRegimen(regimen.id, !regimen.active)}
                      >
                        {regimen.active ? "Pause" : "Resume"}
                      </Button>
                    </div>
                  </div>
                </article>
              ))}
              {regimens.length === 0 && !regimensLoading && (
                <div className="bg-panel border border-dashed border-border-soft rounded-2xl py-16 text-center">
                  <p className="text-sm text-muted-foreground font-medium italic opacity-60">No active regimens observed.</p>
                </div>
              )}
            </div>
          </section>
        </div>

        <aside className="col-span-12 lg:col-span-4 space-y-10 lg:sticky lg:top-28">
          <section className="space-y-6">
            <div className="flex items-center gap-2 px-1">
              <History className="h-4 w-4 text-accent-teal" aria-hidden="true" />
              <h4 className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground">Longitudinal Adherence</h4>
            </div>
            <div className="grid gap-3">
              {adherenceEvents.slice(0, 8).map((event) => (
                <article key={event.id} className="bg-panel border border-border-soft rounded-xl p-4 shadow-sm">
                  <div className="flex items-center justify-between">
                    <Badge variant="outline" className={cn(
                      "text-[9px] font-bold uppercase tracking-widest px-2 py-0.5",
                      event.status === "taken" ? "bg-health-teal/10 text-health-teal border-health-teal/20" : "bg-health-rose/10 text-health-rose border-health-rose/20"
                    )}>
                      {event.status}
                    </Badge>
                    <span className="text-[10px] font-bold text-muted-foreground uppercase">
                      {new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "numeric" }).format(new Date(event.scheduled_at))}
                    </span>
                  </div>
                  <div className="mt-3 text-[13px] font-semibold text-foreground truncate">
                    {regimens.find(r => r.id === event.regimen_id)?.medication_name ?? "Clinical Dosage"}
                  </div>
                </article>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </main>
  );
}
