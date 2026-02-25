"use client";

import { useMemo, useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { JsonViewer } from "@/components/app/json-viewer";
import { PageTitle } from "@/components/app/page-title";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { confirmReminder, generateReminders, listReminders } from "@/lib/api";
import type { ReminderEventView, ReminderMetrics } from "@/lib/types";

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
  const [loadingAction, setLoadingAction] = useState<"generate" | "list" | "yes" | "no" | null>(null);

  const selectableReminders = useMemo(() => reminders.filter((item) => item.status === "sent"), [reminders]);

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
              <Label htmlFor="reminder-select">Confirm reminder</Label>
              <Select
                id="reminder-select"
                value={selectedId}
                onChange={(e) => setSelectedId(e.target.value)}
                disabled={loadingAction !== null}
              >
                <option value="">Select reminder</option>
                {selectableReminders.map((reminder) => (
                  <option key={reminder.id} value={reminder.id}>
                    {reminder.medication_name} {reminder.dosage_text} @{" "}
                    {reminderTimeFormatter.format(new Date(reminder.scheduled_at))}
                  </option>
                ))}
              </Select>
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
          <JsonViewer title="Reminder Events" data={reminders.length ? reminders : null} emptyLabel="No reminders loaded yet." />
        </div>
      </div>
    </div>
  );
}
