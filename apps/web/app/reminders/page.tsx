"use client";

import { useEffect, useMemo, useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  confirmReminder,
  generateReminders,
  listReminderNotificationEndpoints,
  listReminderNotificationLogs,
  listReminderNotificationPreferences,
  listReminderNotificationSchedules,
  listReminders,
  updateReminderNotificationEndpoints,
  updateReminderNotificationPreferences,
} from "@/lib/api";
import type {
  ReminderEventView,
  ReminderMetrics,
  ReminderNotificationEndpoint,
  ReminderNotificationLogItem,
  ReminderNotificationPreferenceRule,
  ScheduledReminderNotificationItem,
} from "@/lib/types";

const reminderTimeFormatter = new Intl.DateTimeFormat(undefined, {
  hour: "numeric",
  minute: "2-digit",
});

function MetricsCard({ metrics }: { metrics: ReminderMetrics | null }) {
  if (!metrics) {
    return <p className="app-muted text-sm">No metrics loaded yet.</p>;
  }
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="metric-card">
        <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Reminders Sent</div>
        <div className="mt-1 text-xl font-semibold">{metrics.reminders_sent}</div>
      </div>
      <div className="metric-card">
        <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Meal Confirmation Rate</div>
        <div className="mt-1 text-xl font-semibold">{(metrics.meal_confirmation_rate * 100).toFixed(1)}%</div>
      </div>
      <div className="metric-card">
        <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Confirmed Yes</div>
        <div className="mt-1 text-xl font-semibold">{metrics.meal_confirmed_yes}</div>
      </div>
      <div className="metric-card">
        <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Confirmed No</div>
        <div className="mt-1 text-xl font-semibold">{metrics.meal_confirmed_no}</div>
      </div>
    </div>
  );
}

export default function RemindersPage() {
  const [reminders, setReminders] = useState<ReminderEventView[]>([]);
  const [metrics, setMetrics] = useState<ReminderMetrics | null>(null);
  const [selectedId, setSelectedId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<"generate" | "list" | "yes" | "no" | "saveSettings" | null>(null);
  const [preferences, setPreferences] = useState<ReminderNotificationPreferenceRule[]>([]);
  const [endpoints, setEndpoints] = useState<ReminderNotificationEndpoint[]>([]);
  const [schedules, setSchedules] = useState<ScheduledReminderNotificationItem[]>([]);
  const [logs, setLogs] = useState<ReminderNotificationLogItem[]>([]);
  const [emailDestination, setEmailDestination] = useState("");
  const [smsDestination, setSmsDestination] = useState("");
  const [emailVerified, setEmailVerified] = useState(true);
  const [smsVerified, setSmsVerified] = useState(false);
  const [inAppEnabled, setInAppEnabled] = useState(true);
  const [inAppOffset, setInAppOffset] = useState(0);
  const [emailEnabled, setEmailEnabled] = useState(false);
  const [emailOffset, setEmailOffset] = useState(0);
  const [smsEnabled, setSmsEnabled] = useState(false);
  const [smsOffset, setSmsOffset] = useState(0);

  const selectableReminders = useMemo(() => reminders.filter((item) => item.status === "sent"), [reminders]);
  const selectedReminder = useMemo(
    () => selectableReminders.find((item) => item.id === selectedId) ?? null,
    [selectableReminders, selectedId],
  );

  async function loadConfigurations() {
    const [preferenceData, endpointData] = await Promise.all([
      listReminderNotificationPreferences(),
      listReminderNotificationEndpoints(),
    ]);
    setPreferences(preferenceData.preferences);
    setEndpoints(endpointData.endpoints);

    const inAppRule = preferenceData.preferences.find((item) => item.channel === "in_app");
    const emailRule = preferenceData.preferences.find((item) => item.channel === "email");
    const smsRule = preferenceData.preferences.find((item) => item.channel === "sms");
    setInAppEnabled(Boolean(inAppRule?.enabled ?? true));
    setInAppOffset(inAppRule?.offset_minutes ?? 0);
    setEmailEnabled(Boolean(emailRule?.enabled));
    setEmailOffset(emailRule?.offset_minutes ?? 0);
    setSmsEnabled(Boolean(smsRule?.enabled));
    setSmsOffset(smsRule?.offset_minutes ?? 0);

    const emailEndpoint = endpointData.endpoints.find((item) => item.channel === "email");
    const smsEndpoint = endpointData.endpoints.find((item) => item.channel === "sms");
    setEmailDestination(emailEndpoint?.destination ?? "");
    setEmailVerified(Boolean(emailEndpoint?.verified ?? true));
    setSmsDestination(smsEndpoint?.destination ?? "");
    setSmsVerified(Boolean(smsEndpoint?.verified));
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
    void loadConfigurations().catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setSchedules([]);
      setLogs([]);
      return;
    }
    void loadReminderDeliveryDetails(selectedId).catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [selectedId]);

  return (
    <div>
      <PageTitle
        eyebrow="Reminders"
        title="Medication Reminder Operations"
        description="Generate demo reminders, refresh persisted events, and confirm meal status with a mobile-friendly workflow."
        tags={["member scopes", "MCR metrics"]}
      />

      <div className="page-grid">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Reminder Actions</CardTitle>
            <CardDescription>Generate and confirm reminder events using the FastAPI reminder endpoints.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <Button
                disabled={loadingAction !== null}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("generate");
                  try {
                    const data = await generateReminders();
                    setReminders(data.reminders);
                    setMetrics(data.metrics);
                    if (data.reminders[0]) setSelectedId(data.reminders[0].id);
                    await loadConfigurations();
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
                  setLoadingAction("list");
                  try {
                    const data = await listReminders();
                    setReminders(data.reminders);
                    setMetrics(data.metrics);
                    if (data.reminders[0]) setSelectedId(data.reminders[0].id);
                    await loadConfigurations();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "list"} loading="Refreshing" idle="Refresh List" />
              </Button>
            </div>

            <div className="space-y-2">
              <Label>Confirm reminder</Label>
              {selectableReminders.length > 0 ? (
                <div className="data-list">
                  {selectableReminders.slice(0, 5).map((reminder) => {
                    const active = selectedId === reminder.id;
                    return (
                      <button
                        key={reminder.id}
                        type="button"
                        disabled={loadingAction !== null}
                        onClick={() => setSelectedId(reminder.id)}
                        className={[
                          "w-full rounded-xl border px-3 py-3 text-left transition",
                          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring)] focus-visible:ring-offset-2",
                          "focus-visible:ring-offset-[color:var(--background)]",
                          active
                            ? "border-[color:var(--accent)]/40 bg-[color:var(--accent)]/10"
                            : "border-[color:var(--border)] bg-white/60 hover:bg-white/80 dark:bg-[color:var(--panel-soft)] dark:hover:bg-[color:var(--card)]",
                        ].join(" ")}
                        aria-pressed={active}
                      >
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                          <div className="min-w-0">
                            <div className="truncate text-sm font-medium">
                              {reminder.medication_name} {reminder.dosage_text}
                            </div>
                            <div className="app-muted mt-1 text-xs">
                              {new Intl.DateTimeFormat(undefined, {
                                dateStyle: "medium",
                                timeStyle: "short",
                              }).format(new Date(reminder.scheduled_at))}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="rounded-full border border-[color:var(--border)] px-2 py-1 text-xs">
                              {active ? "Selected" : "Tap to select"}
                            </span>
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-[color:var(--border)] bg-white/40 p-3 text-sm text-[color:var(--muted-foreground)] dark:bg-[color:var(--panel-soft)]/70">
                  Generate or refresh reminders first. Only reminders with `sent` status can be confirmed.
                </div>
              )}
              {selectedReminder ? (
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Selected Reminder</div>
                  <div className="mt-1 text-sm font-medium">
                    {selectedReminder.medication_name} {selectedReminder.dosage_text}
                  </div>
                  <div className="app-muted mt-1 text-xs">
                    Scheduled {new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(selectedReminder.scheduled_at))}
                  </div>
                </div>
              ) : null}
              <p className="app-muted text-xs">Only reminders with `sent` status are available for confirmation.</p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                disabled={!selectedId || loadingAction !== null}
                onClick={async () => {
                  if (!selectedId) return;
                  setError(null);
                  setLoadingAction("yes");
                  try {
                    const data = await confirmReminder(selectedId, true);
                    setMetrics(data.metrics);
                    const refreshed = await listReminders();
                    setReminders(refreshed.reminders);
                    await loadReminderDeliveryDetails(selectedId);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "yes"} loading="Saving" idle="Confirm Yes" />
              </Button>
              <Button
                variant="secondary"
                disabled={!selectedId || loadingAction !== null}
                onClick={async () => {
                  if (!selectedId) return;
                  setError(null);
                  setLoadingAction("no");
                  try {
                    const data = await confirmReminder(selectedId, false);
                    setMetrics(data.metrics);
                    const refreshed = await listReminders();
                    setReminders(refreshed.reminders);
                    await loadReminderDeliveryDetails(selectedId);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "no"} loading="Saving" idle="Confirm No" />
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="stack-grid">
          {error ? <ErrorCard message={error} /> : null}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Metrics</CardTitle>
              <CardDescription>Meal confirmation rate and reminder totals.</CardDescription>
            </CardHeader>
            <CardContent>
              <MetricsCard metrics={metrics} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Delivery Settings</CardTitle>
              <CardDescription>Persist channel rules and contact endpoints per user.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">In-app</div>
                  <Label className="mt-2 flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={inAppEnabled} onChange={(e) => setInAppEnabled(e.target.checked)} />
                    Enabled
                  </Label>
                  <Label className="mt-2 block text-xs">Offset minutes</Label>
                  <input
                    className="mt-1 w-full rounded-lg border border-[color:var(--border)] bg-transparent px-3 py-2 text-sm"
                    type="number"
                    max={0}
                    value={inAppOffset}
                    onChange={(e) => setInAppOffset(Number(e.target.value))}
                  />
                </div>
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Email</div>
                  <Label className="mt-2 flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={emailEnabled} onChange={(e) => setEmailEnabled(e.target.checked)} />
                    Enabled
                  </Label>
                  <Label className="mt-2 block text-xs">Destination</Label>
                  <input
                    className="mt-1 w-full rounded-lg border border-[color:var(--border)] bg-transparent px-3 py-2 text-sm"
                    value={emailDestination}
                    onChange={(e) => setEmailDestination(e.target.value)}
                    placeholder="name@example.com"
                  />
                  <Label className="mt-2 flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={emailVerified} onChange={(e) => setEmailVerified(e.target.checked)} />
                    Verified
                  </Label>
                  <Label className="mt-2 block text-xs">Offset minutes</Label>
                  <input
                    className="mt-1 w-full rounded-lg border border-[color:var(--border)] bg-transparent px-3 py-2 text-sm"
                    type="number"
                    max={0}
                    value={emailOffset}
                    onChange={(e) => setEmailOffset(Number(e.target.value))}
                  />
                </div>
                <div className="metric-card md:col-span-2">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">SMS</div>
                  <div className="grid gap-3 md:grid-cols-[auto,1fr,auto] md:items-center">
                    <Label className="flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={smsEnabled} onChange={(e) => setSmsEnabled(e.target.checked)} />
                      Enabled
                    </Label>
                    <input
                      className="w-full rounded-lg border border-[color:var(--border)] bg-transparent px-3 py-2 text-sm"
                      value={smsDestination}
                      onChange={(e) => setSmsDestination(e.target.value)}
                      placeholder="+15551234567"
                    />
                    <input
                      className="w-full rounded-lg border border-[color:var(--border)] bg-transparent px-3 py-2 text-sm md:w-28"
                      type="number"
                      max={0}
                      value={smsOffset}
                      onChange={(e) => setSmsOffset(Number(e.target.value))}
                    />
                  </div>
                  <Label className="mt-2 flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={smsVerified} onChange={(e) => setSmsVerified(e.target.checked)} />
                    Verified
                  </Label>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  disabled={loadingAction !== null}
                  onClick={async () => {
                    setError(null);
                    setLoadingAction("saveSettings");
                    try {
                      await Promise.all([
                        updateReminderNotificationPreferences({
                          rules: [
                            { channel: "in_app", offset_minutes: inAppOffset, enabled: inAppEnabled },
                            { channel: "email", offset_minutes: emailOffset, enabled: emailEnabled },
                            { channel: "sms", offset_minutes: smsOffset, enabled: smsEnabled },
                          ],
                        }),
                        updateReminderNotificationEndpoints({
                          endpoints: [
                            ...(emailDestination ? [{ channel: "email", destination: emailDestination, verified: emailVerified }] : []),
                            ...(smsDestination ? [{ channel: "sms", destination: smsDestination, verified: smsVerified }] : []),
                          ],
                        }),
                      ]);
                      await loadConfigurations();
                      if (selectedId) {
                        await loadReminderDeliveryDetails(selectedId);
                      }
                    } catch (e) {
                      setError(e instanceof Error ? e.message : String(e));
                    } finally {
                      setLoadingAction(null);
                    }
                  }}
                >
                  <AsyncLabel active={loadingAction === "saveSettings"} loading="Saving" idle="Save Delivery Settings" />
                </Button>
              </div>
              <div className="app-muted text-xs">
                Active rules: {preferences.length}. Configured endpoints: {endpoints.length}.
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Reminder Events</CardTitle>
              <CardDescription>Current events with confirmation state and schedule time.</CardDescription>
            </CardHeader>
            <CardContent>
              {reminders.length > 0 ? (
                <div className="data-list">
                  {reminders.map((reminder) => (
                    <div key={reminder.id} className="data-list-row sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <div className="text-sm font-medium">
                          {reminder.medication_name} {reminder.dosage_text}
                        </div>
                        <div className="app-muted mt-1 text-xs">
                          {new Intl.DateTimeFormat(undefined, {
                            dateStyle: "medium",
                            timeStyle: "short",
                          }).format(new Date(reminder.scheduled_at))}
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 text-xs">
                        <span className="rounded-full border border-[color:var(--border)] px-2 py-1">{reminder.status}</span>
                        <span className="rounded-full border border-[color:var(--border)] px-2 py-1">
                          meal: {reminder.meal_confirmation}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="app-muted text-sm">No reminders loaded yet.</p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Delivery Schedule</CardTitle>
              <CardDescription>Materialized notification jobs for the selected reminder.</CardDescription>
            </CardHeader>
            <CardContent>
              {selectedId && schedules.length > 0 ? (
                <div className="data-list">
                  {schedules.map((item) => (
                    <div key={item.id} className="data-list-row">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <div className="text-sm font-medium">{item.channel}</div>
                          <div className="app-muted text-xs">
                            Trigger {new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(item.trigger_at))}
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-2 text-xs">
                          <span className="rounded-full border border-[color:var(--border)] px-2 py-1">{item.status}</span>
                          <span className="rounded-full border border-[color:var(--border)] px-2 py-1">{item.offset_minutes} min</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="app-muted text-sm">Select a reminder to inspect scheduled notifications.</p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Delivery Logs</CardTitle>
              <CardDescription>Immutable attempt history for the selected reminder.</CardDescription>
            </CardHeader>
            <CardContent>
              {selectedId && logs.length > 0 ? (
                <div className="data-list">
                  {logs.map((item) => (
                    <div key={item.id} className="data-list-row">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <div className="text-sm font-medium">{item.event_type}</div>
                          <div className="app-muted text-xs">
                            {new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(item.created_at))}
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-2 text-xs">
                          <span className="rounded-full border border-[color:var(--border)] px-2 py-1">{item.channel}</span>
                          <span className="rounded-full border border-[color:var(--border)] px-2 py-1">attempt {item.attempt_number}</span>
                        </div>
                      </div>
                      {item.error_message ? <div className="mt-2 text-xs text-amber-700 dark:text-amber-300">{item.error_message}</div> : null}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="app-muted text-sm">Delivery logs appear after a reminder has been queued or delivered.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
