"use client";

import { useEffect, useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  createMedicationAdherenceEvent,
  createMedicationRegimen,
  deleteMedicationRegimen,
  getMedicationAdherenceMetrics,
  listMedicationRegimens,
} from "@/lib/api";
import type { MedicationAdherenceMetricsApiResponse, MedicationRegimenApi } from "@/lib/types";

type LoadingAction = "refresh" | "createRegimen" | "deleteRegimen" | "createAdherence" | null;

function nowLocalDateTimeInput(): string {
  const now = new Date();
  now.setSeconds(0, 0);
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function toIsoFromDateTimeInput(value: string): string | null {
  if (!value.trim()) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toISOString();
}

export default function MedicationsPage() {
  const [regimens, setRegimens] = useState<MedicationRegimenApi[]>([]);
  const [metrics, setMetrics] = useState<MedicationAdherenceMetricsApiResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<LoadingAction>(null);

  const [medicationName, setMedicationName] = useState("Lisinopril");
  const [dosageText, setDosageText] = useState("10mg");
  const [timingType, setTimingType] = useState<"pre_meal" | "post_meal" | "fixed_time">("fixed_time");
  const [fixedTime, setFixedTime] = useState("09:00");
  const [maxDailyDoses, setMaxDailyDoses] = useState("1");
  const [active, setActive] = useState(true);

  const [selectedRegimenId, setSelectedRegimenId] = useState("");
  const [adherenceStatus, setAdherenceStatus] = useState<"taken" | "missed" | "skipped" | "unknown">("taken");
  const [scheduledAtInput, setScheduledAtInput] = useState(nowLocalDateTimeInput());
  const [takenAtInput, setTakenAtInput] = useState(nowLocalDateTimeInput());

  async function refreshData() {
    const [regimenResponse, metricsResponse] = await Promise.all([
      listMedicationRegimens(),
      getMedicationAdherenceMetrics(),
    ]);
    setRegimens(regimenResponse.items);
    setMetrics(metricsResponse);
    if (!selectedRegimenId && regimenResponse.items[0]) {
      setSelectedRegimenId(regimenResponse.items[0].id);
    }
  }

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoadingAction("refresh");
        const [regimenResponse, metricsResponse] = await Promise.all([
          listMedicationRegimens(),
          getMedicationAdherenceMetrics(),
        ]);
        if (cancelled) return;
        setRegimens(regimenResponse.items);
        setMetrics(metricsResponse);
        if (regimenResponse.items[0]) {
          setSelectedRegimenId(regimenResponse.items[0].id);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoadingAction(null);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <PageTitle
        eyebrow="Medications"
        title="Medication Tracking and Adherence"
        description="Manage medication regimens and log adherence events with computed adherence metrics."
        tags={["regimens", "adherence", "member scope"]}
      />

      <div className="page-grid">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Regimen Management</CardTitle>
            <CardDescription>Create and remove user-scoped medication schedules used by reminders and adherence tracking.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="medication-name">Medication name</Label>
                <Input
                  id="medication-name"
                  value={medicationName}
                  onChange={(event) => setMedicationName(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="dosage-text">Dosage</Label>
                <Input
                  id="dosage-text"
                  value={dosageText}
                  onChange={(event) => setDosageText(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="timing-type">Timing</Label>
                <Select
                  id="timing-type"
                  value={timingType}
                  onChange={(event) => setTimingType(event.target.value as "pre_meal" | "post_meal" | "fixed_time")}
                >
                  <option value="fixed_time">Fixed time</option>
                  <option value="pre_meal">Pre-meal</option>
                  <option value="post_meal">Post-meal</option>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="fixed-time">Fixed time (HH:MM)</Label>
                <Input
                  id="fixed-time"
                  type="time"
                  value={fixedTime}
                  onChange={(event) => setFixedTime(event.target.value)}
                  disabled={timingType !== "fixed_time"}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="max-daily-doses">Max daily doses</Label>
                <Input
                  id="max-daily-doses"
                  type="number"
                  min={1}
                  max={8}
                  value={maxDailyDoses}
                  onChange={(event) => setMaxDailyDoses(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label className="flex items-center gap-2 pt-7 text-sm">
                  <input
                    type="checkbox"
                    checked={active}
                    onChange={(event) => setActive(event.target.checked)}
                  />
                  Active regimen
                </Label>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                disabled={loadingAction !== null || !medicationName.trim() || !dosageText.trim()}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("createRegimen");
                  try {
                    const maxDoses = Math.max(1, Math.min(8, Number(maxDailyDoses) || 1));
                    await createMedicationRegimen({
                      medication_name: medicationName.trim(),
                      dosage_text: dosageText.trim(),
                      timing_type: timingType,
                      fixed_time: timingType === "fixed_time" ? fixedTime : null,
                      offset_minutes: 0,
                      slot_scope: [],
                      max_daily_doses: maxDoses,
                      active,
                    });
                    await refreshData();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "createRegimen"} idle="Create Regimen" loading="Creating" />
              </Button>
              <Button
                variant="secondary"
                disabled={loadingAction !== null}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("refresh");
                  try {
                    await refreshData();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "refresh"} idle="Refresh Data" loading="Refreshing" />
              </Button>
            </div>

            <div className="space-y-2">
              <div className="text-sm font-semibold">Active regimens</div>
              {regimens.length > 0 ? (
                <div className="data-list">
                  {regimens.map((regimen) => (
                    <div key={regimen.id} className="data-list-row gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <div className="text-sm font-medium">
                          {regimen.medication_name} · {regimen.dosage_text}
                        </div>
                        <div className="app-muted mt-1 text-xs">
                          {regimen.timing_type === "fixed_time"
                            ? `Fixed at ${regimen.fixed_time ?? "unset"}`
                            : regimen.timing_type}
                          {" · "}
                          {regimen.active ? "active" : "inactive"}
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={loadingAction !== null}
                        onClick={async () => {
                          setError(null);
                          setLoadingAction("deleteRegimen");
                          try {
                            await deleteMedicationRegimen(regimen.id);
                            await refreshData();
                            if (selectedRegimenId === regimen.id) {
                              const next = regimens.find((item) => item.id !== regimen.id);
                              setSelectedRegimenId(next?.id ?? "");
                            }
                          } catch (e) {
                            setError(e instanceof Error ? e.message : String(e));
                          } finally {
                            setLoadingAction(null);
                          }
                        }}
                      >
                        Delete
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="app-muted text-sm">No regimens yet. Create one to start adherence tracking.</p>
              )}
            </div>
          </CardContent>
        </Card>

        <div className="stack-grid">
          {error ? <ErrorCard message={error} /> : null}
          <Card>
            <CardHeader>
              <CardTitle>Adherence Event Logging</CardTitle>
              <CardDescription>Capture `taken`, `missed`, or `skipped` events and update adherence metrics in real time.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="adherence-regimen">Regimen</Label>
                  <Select
                    id="adherence-regimen"
                    value={selectedRegimenId}
                    onChange={(event) => setSelectedRegimenId(event.target.value)}
                  >
                    <option value="">Select regimen</option>
                    {regimens.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.medication_name} ({item.dosage_text})
                      </option>
                    ))}
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="adherence-status">Status</Label>
                  <Select
                    id="adherence-status"
                    value={adherenceStatus}
                    onChange={(event) =>
                      setAdherenceStatus(event.target.value as "taken" | "missed" | "skipped" | "unknown")
                    }
                  >
                    <option value="taken">Taken</option>
                    <option value="missed">Missed</option>
                    <option value="skipped">Skipped</option>
                    <option value="unknown">Unknown</option>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="scheduled-at">Scheduled at</Label>
                  <Input
                    id="scheduled-at"
                    type="datetime-local"
                    value={scheduledAtInput}
                    onChange={(event) => setScheduledAtInput(event.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="taken-at">Taken at (optional)</Label>
                  <Input
                    id="taken-at"
                    type="datetime-local"
                    value={takenAtInput}
                    onChange={(event) => setTakenAtInput(event.target.value)}
                    disabled={adherenceStatus !== "taken"}
                  />
                </div>
              </div>
              <Button
                disabled={loadingAction !== null || !selectedRegimenId}
                onClick={async () => {
                  const scheduledAt = toIsoFromDateTimeInput(scheduledAtInput);
                  const takenAt = adherenceStatus === "taken" ? toIsoFromDateTimeInput(takenAtInput) : null;
                  if (!scheduledAt) {
                    setError("Scheduled time is required.");
                    return;
                  }
                  setError(null);
                  setLoadingAction("createAdherence");
                  try {
                    await createMedicationAdherenceEvent({
                      regimen_id: selectedRegimenId,
                      status: adherenceStatus,
                      scheduled_at: scheduledAt,
                      taken_at: takenAt,
                      source: "manual",
                      metadata: {},
                    });
                    await refreshData();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "createAdherence"} idle="Log Adherence Event" loading="Logging" />
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Adherence Metrics</CardTitle>
              <CardDescription>Computed totals from persisted adherence events.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Events</div>
                  <div className="mt-1 text-xl font-semibold">{metrics?.totals.events ?? 0}</div>
                </div>
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Adherence rate</div>
                  <div className="mt-1 text-xl font-semibold">{((metrics?.totals.adherence_rate ?? 0) * 100).toFixed(1)}%</div>
                </div>
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Taken</div>
                  <div className="mt-1 text-xl font-semibold">{metrics?.totals.taken ?? 0}</div>
                </div>
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Missed + skipped</div>
                  <div className="mt-1 text-xl font-semibold">{(metrics?.totals.missed ?? 0) + (metrics?.totals.skipped ?? 0)}</div>
                </div>
              </div>
              {metrics?.events.length ? (
                <div className="data-list mt-3">
                  {metrics.events.slice(0, 8).map((event) => (
                    <div key={event.id} className="data-list-row">
                      <div className="text-sm font-medium">{event.status.toUpperCase()}</div>
                      <div className="app-muted text-xs">{new Date(event.scheduled_at).toLocaleString()}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="app-muted mt-3 text-sm">No adherence events logged yet.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
