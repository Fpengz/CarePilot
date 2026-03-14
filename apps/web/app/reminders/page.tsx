"use client";

import { useEffect, useMemo, useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  actOnReminderOccurrence,
  generateReminders,
  listReminderDefinitions,
  listReminderHistory,
  listReminderNotificationLogs,
  listReminderNotificationSchedules,
  listReminders,
  listUpcomingReminderOccurrences,
} from "@/lib/api/reminder-client";
import type {
  ReminderDefinitionApi,
  ReminderEventView,
  ReminderMetrics,
  ReminderNotificationLogItem,
  ReminderOccurrenceApi,
  ScheduledReminderNotificationItem,
} from "@/lib/types";

const timestampFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

function MetricsCard({ metrics }: { metrics: ReminderMetrics | null }) {
  if (!metrics) {
    return <p className="app-muted text-sm">Generate or refresh reminders to load adherence metrics.</p>;
  }
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="metric-card">
        <div className="text-xs uppercase tracking-[0.24em] text-[color:var(--muted-foreground)]">Reminders Sent</div>
        <div className="mt-2 text-2xl font-semibold">{metrics.reminders_sent}</div>
      </div>
      <div className="metric-card">
        <div className="text-xs uppercase tracking-[0.24em] text-[color:var(--muted-foreground)]">Confirmation Rate</div>
        <div className="mt-2 text-2xl font-semibold">{(metrics.meal_confirmation_rate * 100).toFixed(1)}%</div>
      </div>
      <div className="metric-card">
        <div className="text-xs uppercase tracking-[0.24em] text-[color:var(--muted-foreground)]">Taken / Yes</div>
        <div className="mt-2 text-2xl font-semibold">{metrics.meal_confirmed_yes}</div>
      </div>
      <div className="metric-card">
        <div className="text-xs uppercase tracking-[0.24em] text-[color:var(--muted-foreground)]">Skipped / No</div>
        <div className="mt-2 text-2xl font-semibold">{metrics.meal_confirmed_no}</div>
      </div>
    </div>
  );
}

function scheduleSummary(definition: ReminderDefinitionApi) {
  const { schedule } = definition;
  if (schedule.pattern === "daily_fixed_times") {
    return `Daily at ${schedule.times.join(", ")}`;
  }
  if (schedule.pattern === "meal_relative") {
    const slot = schedule.meal_slot ?? "meal";
    const direction = schedule.relative_direction ?? "after";
    const offset = schedule.offset_minutes ? ` (${schedule.offset_minutes} min)` : "";
    return `${direction === "before" ? "Before" : "After"} ${slot}${offset}`;
  }
  if (schedule.pattern === "every_x_hours") {
    return `Every ${schedule.interval_hours ?? "?"} hours`;
  }
  if (schedule.pattern === "specific_weekdays") {
    return `Weekdays ${schedule.weekdays.join(", ")}`;
  }
  if (schedule.pattern === "bedtime") {
    return "Before sleep";
  }
  if (schedule.pattern === "prn") {
    return `As needed${schedule.max_daily_occurrences ? `, max ${schedule.max_daily_occurrences}/day` : ""}`;
  }
  if (schedule.pattern === "temporary_course") {
    return `Temporary course${schedule.end_date ? ` until ${schedule.end_date}` : ""}`;
  }
  return "Structured reminder";
}

function statusTone(status: ReminderOccurrenceApi["status"]) {
  if (status === "completed") return "bg-emerald-100 text-emerald-800";
  if (status === "missed" || status === "skipped") return "bg-rose-100 text-rose-800";
  if (status === "snoozed") return "bg-amber-100 text-amber-900";
  return "bg-[color:var(--accent)]/10 text-[color:var(--foreground)]";
}

export default function RemindersPage() {
  const [definitions, setDefinitions] = useState<ReminderDefinitionApi[]>([]);
  const [upcoming, setUpcoming] = useState<ReminderOccurrenceApi[]>([]);
  const [history, setHistory] = useState<ReminderOccurrenceApi[]>([]);
  const [reminders, setReminders] = useState<ReminderEventView[]>([]);
  const [metrics, setMetrics] = useState<ReminderMetrics | null>(null);
  const [selectedOccurrenceId, setSelectedOccurrenceId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<"generate" | "refresh" | "taken" | "skipped" | "snooze10" | "snooze30" | null>(null);
  const [schedules, setSchedules] = useState<ScheduledReminderNotificationItem[]>([]);
  const [logs, setLogs] = useState<ReminderNotificationLogItem[]>([]);

  const definitionMap = useMemo(() => new Map(definitions.map((item) => [item.id, item])), [definitions]);
  const selectedOccurrence = useMemo(
    () => [...upcoming, ...history].find((item) => item.id === selectedOccurrenceId) ?? null,
    [history, selectedOccurrenceId, upcoming],
  );
  const selectedDefinition = selectedOccurrence ? definitionMap.get(selectedOccurrence.reminder_definition_id) ?? null : null;

  async function loadStructuredData() {
    const [definitionData, upcomingData, historyData, reminderData] = await Promise.all([
      listReminderDefinitions(),
      listUpcomingReminderOccurrences(),
      listReminderHistory(),
      listReminders(),
    ]);
    setDefinitions(definitionData.items);
    setUpcoming(upcomingData.items);
    setHistory(historyData.items);
    setReminders(reminderData.reminders);
    setMetrics(reminderData.metrics);
    const nextSelected = selectedOccurrenceId || upcomingData.items[0]?.id || historyData.items[0]?.id || "";
    setSelectedOccurrenceId(nextSelected);
  }

  async function loadReminderDeliveryDetails(reminderId: string) {
    const [scheduleData, logData] = await Promise.all([
      listReminderNotificationSchedules(reminderId),
      listReminderNotificationLogs(reminderId),
    ]);
    setSchedules(scheduleData.items);
    setLogs(logData.items);
  }

  useEffect(() => {
    if (!selectedOccurrenceId) {
      setSchedules([]);
      setLogs([]);
      return;
    }
    void loadReminderDeliveryDetails(selectedOccurrenceId).catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [selectedOccurrenceId]);

  async function runOccurrenceAction(
    action: "taken" | "skipped" | "snooze",
    loadingState: "taken" | "skipped" | "snooze10" | "snooze30",
    snoozeMinutes?: number,
  ) {
    if (!selectedOccurrenceId) return;
    setError(null);
    setLoadingAction(loadingState);
    try {
      await actOnReminderOccurrence({
        occurrenceId: selectedOccurrenceId,
        action,
        snooze_minutes: snoozeMinutes,
      });
      await loadStructuredData();
      await loadReminderDeliveryDetails(selectedOccurrenceId);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingAction(null);
    }
  }

  return (
    <div>
      <PageTitle
        eyebrow="Reminders"
        title="Structured Reminders"
        description="Track active reminder plans, upcoming care events, history, and multi-channel delivery without leaving the reminders workspace."
      />

      <div className="page-grid">
        <Card className="grain-overlay border-[color:var(--border)] bg-[color:var(--card)]">
          <CardHeader>
            <CardTitle>Reminder Console</CardTitle>
            <CardDescription>Generate projections from today&apos;s reminder definitions, then act on the queued occurrences.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="flex flex-wrap gap-2">
              <Button
                disabled={loadingAction !== null}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("generate");
                  try {
                    const generated = await generateReminders();
                    setReminders(generated.reminders);
                    setMetrics(generated.metrics);
                    await loadStructuredData();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "generate"} loading="Generating" idle="Generate Today Reminders" />
              </Button>
              <Button
                variant="secondary"
                disabled={loadingAction !== null}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("refresh");
                  try {
                    await loadStructuredData();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "refresh"} loading="Refreshing" idle="Refresh Structured View" />
              </Button>
            </div>

            {selectedOccurrence ? (
              <div className="rounded-[1.25rem] border border-[color:var(--border)] bg-[linear-gradient(145deg,color-mix(in_oklab,var(--accent)_12%,white),transparent)] p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-2">
                    <div className="text-xs uppercase tracking-[0.28em] text-[color:var(--muted-foreground)]">Selected occurrence</div>
                    <div className="text-lg font-semibold">{selectedDefinition?.title ?? "Reminder occurrence"}</div>
                    <div className="text-sm text-[color:var(--muted-foreground)]">
                      {selectedDefinition?.body ?? selectedDefinition?.instructions_text ?? "No summary available."}
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs text-[color:var(--muted-foreground)]">
                      <span>{timestampFormatter.format(new Date(selectedOccurrence.trigger_at))}</span>
                      <span>Grace {selectedOccurrence.grace_window_minutes}m</span>
                      <span>{selectedDefinition ? scheduleSummary(selectedDefinition) : "Structured occurrence"}</span>
                    </div>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-xs font-medium ${statusTone(selectedOccurrence.status)}`}>
                    {selectedOccurrence.status}
                  </span>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button disabled={loadingAction !== null} onClick={() => void runOccurrenceAction("taken", "taken")}>
                    <AsyncLabel active={loadingAction === "taken"} loading="Saving" idle="Taken" />
                  </Button>
                  <Button variant="secondary" disabled={loadingAction !== null} onClick={() => void runOccurrenceAction("skipped", "skipped")}>
                    <AsyncLabel active={loadingAction === "skipped"} loading="Saving" idle="Skipped" />
                  </Button>
                  <Button variant="secondary" disabled={loadingAction !== null} onClick={() => void runOccurrenceAction("snooze", "snooze10", 10)}>
                    <AsyncLabel active={loadingAction === "snooze10"} loading="Snoozing" idle="Snooze 10m" />
                  </Button>
                  <Button variant="secondary" disabled={loadingAction !== null} onClick={() => void runOccurrenceAction("snooze", "snooze30", 30)}>
                    <AsyncLabel active={loadingAction === "snooze30"} loading="Snoozing" idle="Snooze 30m" />
                  </Button>
                </div>
              </div>
            ) : (
              <div className="rounded-[1.25rem] border border-dashed border-[color:var(--border)] bg-[color:var(--card)]/60 p-4 text-sm text-[color:var(--muted-foreground)]">
                Generate reminders or refresh the structured view to load an actionable occurrence.
              </div>
            )}

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-[1rem] border border-[color:var(--border)] bg-[color:var(--card)]/80 p-4">
                <div className="text-xs uppercase tracking-[0.24em] text-[color:var(--muted-foreground)]">Projected events</div>
                <div className="mt-2 text-3xl font-semibold">{upcoming.length}</div>
                <div className="mt-1 text-sm text-[color:var(--muted-foreground)]">Ready in the upcoming queue.</div>
              </div>
              <div className="rounded-[1rem] border border-[color:var(--border)] bg-[color:var(--card)]/80 p-4">
                <div className="text-xs uppercase tracking-[0.24em] text-[color:var(--muted-foreground)]">Tracked plans</div>
                <div className="mt-2 text-3xl font-semibold">{definitions.length}</div>
                <div className="mt-1 text-sm text-[color:var(--muted-foreground)]">Structured reminder definitions currently active.</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="section-stack">
          {error ? <ErrorCard message={error} /> : null}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Metrics</CardTitle>
              <CardDescription>Legacy reminder metrics remain visible while the structured flow rolls out.</CardDescription>
            </CardHeader>
            <CardContent>
              <MetricsCard metrics={metrics} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Active Reminders</CardTitle>
              <CardDescription>Structured reminder definitions with schedule semantics, channels, and medication context.</CardDescription>
            </CardHeader>
            <CardContent>
              {definitions.length > 0 ? (
                <div className="data-list">
                  {definitions.map((definition) => (
                    <div key={definition.id} className="data-list-row gap-3">
                      <div className="min-w-0 space-y-1">
                        <div className="text-sm font-medium">{definition.title}</div>
                        <div className="text-xs text-[color:var(--muted-foreground)]">
                          {definition.body ?? definition.instructions_text ?? `${definition.medication_name} ${definition.dosage_text}`}
                        </div>
                        <div className="flex flex-wrap gap-2 text-xs text-[color:var(--muted-foreground)]">
                          <span>{scheduleSummary(definition)}</span>
                          <span>{definition.channels.join(" + ")}</span>
                          <span>{definition.timezone}</span>
                        </div>
                      </div>
                      <span className="rounded-full border border-[color:var(--border)] px-2 py-1 text-xs">
                        {definition.active ? "active" : "paused"}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="app-muted text-sm">No structured reminder definitions loaded yet.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Upcoming Queue</CardTitle>
              <CardDescription>Actionable reminder occurrences sorted by next trigger time.</CardDescription>
            </CardHeader>
            <CardContent>
              {upcoming.length > 0 ? (
                <div className="data-list">
                  {upcoming.map((occurrence) => {
                    const active = selectedOccurrenceId === occurrence.id;
                    const definition = definitionMap.get(occurrence.reminder_definition_id);
                    return (
                      <button
                        key={occurrence.id}
                        type="button"
                        onClick={() => setSelectedOccurrenceId(occurrence.id)}
                        className={[
                          "w-full rounded-[1rem] border px-3 py-3 text-left transition",
                          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring)] focus-visible:ring-offset-2",
                          "focus-visible:ring-offset-[color:var(--background)]",
                          active ? "border-[color:var(--accent)] bg-[color:var(--accent)]/10" : "border-[color:var(--border)] bg-white/60 hover:bg-white/80 dark:bg-[color:var(--panel-soft)] dark:hover:bg-[color:var(--card)]",
                        ].join(" ")}
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="min-w-0 space-y-1">
                            <div className="text-sm font-medium">{definition?.title ?? "Reminder occurrence"}</div>
                            <div className="text-xs text-[color:var(--muted-foreground)]">
                              {definition?.body ?? definition?.instructions_text ?? "Structured occurrence"}
                            </div>
                            <div className="text-xs text-[color:var(--muted-foreground)]">{timestampFormatter.format(new Date(occurrence.trigger_at))}</div>
                          </div>
                          <span className={`rounded-full px-2 py-1 text-xs font-medium ${statusTone(occurrence.status)}`}>
                            {occurrence.status}
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              ) : (
                <p className="app-muted text-sm">No upcoming occurrences queued yet.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Recent History</CardTitle>
              <CardDescription>Completed, skipped, snoozed, and missed reminder outcomes.</CardDescription>
            </CardHeader>
            <CardContent>
              {history.length > 0 ? (
                <div className="data-list">
                  {history.map((occurrence) => {
                    const definition = definitionMap.get(occurrence.reminder_definition_id);
                    return (
                      <div key={occurrence.id} className="data-list-row gap-3">
                        <div className="min-w-0 space-y-1">
                          <div className="text-sm font-medium">{definition?.title ?? "Reminder occurrence"}</div>
                          <div className="text-xs text-[color:var(--muted-foreground)]">
                            {occurrence.action ? `${occurrence.action} · ` : ""}
                            {timestampFormatter.format(new Date(occurrence.acted_at ?? occurrence.updated_at))}
                          </div>
                        </div>
                        <span className={`rounded-full px-2 py-1 text-xs font-medium ${statusTone(occurrence.status)}`}>
                          {occurrence.status}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="app-muted text-sm">No reminder history yet.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Delivery Detail</CardTitle>
              <CardDescription>Materialized notification jobs and delivery logs for the selected occurrence.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="mb-2 text-xs uppercase tracking-[0.24em] text-[color:var(--muted-foreground)]">Scheduled notifications</div>
                {schedules.length > 0 ? (
                  <div className="data-list">
                    {schedules.map((item) => (
                      <div key={item.id} className="data-list-row sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <div className="text-sm font-medium">{item.channel}</div>
                          <div className="text-xs text-[color:var(--muted-foreground)]">{timestampFormatter.format(new Date(item.trigger_at))}</div>
                        </div>
                        <span className="rounded-full border border-[color:var(--border)] px-2 py-1 text-xs">{item.status}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="app-muted text-sm">No delivery rows for the selected occurrence.</p>
                )}
              </div>

              <div>
                <div className="mb-2 text-xs uppercase tracking-[0.24em] text-[color:var(--muted-foreground)]">Notification log</div>
                {logs.length > 0 ? (
                  <div className="data-list">
                    {logs.map((log) => (
                      <div key={log.id} className="data-list-row sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <div className="text-sm font-medium">{log.event_type}</div>
                          <div className="text-xs text-[color:var(--muted-foreground)]">
                            {log.channel} · {timestampFormatter.format(new Date(log.created_at))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="app-muted text-sm">No notification log rows for the selected occurrence.</p>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Legacy Event Projection</CardTitle>
              <CardDescription>The existing reminder event list stays visible during the migration to structured reminder truth.</CardDescription>
            </CardHeader>
            <CardContent>
              {reminders.length > 0 ? (
                <div className="data-list">
                  {reminders.map((reminder) => (
                    <div key={reminder.id} className="data-list-row sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <div className="text-sm font-medium">{reminder.title}</div>
                        <div className="text-xs text-[color:var(--muted-foreground)]">
                          {reminder.body ?? "Reminder"} · {timestampFormatter.format(new Date(reminder.scheduled_at))}
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2 text-xs">
                        <span className="rounded-full border border-[color:var(--border)] px-2 py-1">{reminder.reminder_type}</span>
                        <span className="rounded-full border border-[color:var(--border)] px-2 py-1">{reminder.status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="app-muted text-sm">No legacy reminder events loaded yet.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
