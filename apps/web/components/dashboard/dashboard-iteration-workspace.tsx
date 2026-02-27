"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Loader2 } from "lucide-react";

import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { useSession } from "@/components/app/session-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import {
  generateSuggestionFromReport,
  getAlertTimeline,
  getWorkflow,
  listMealRecords,
  listReminders,
  listSuggestions,
  listWorkflows,
} from "@/lib/api";
import type {
  ReminderEventView,
  SuggestionGenerateApiResponse,
  SuggestionListApiResponse,
  WorkflowExecutionResult,
} from "@/lib/types";

type Scope = "self" | "household";

function toErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function isoDay(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toISOString().slice(0, 10);
}

export function DashboardIterationWorkspace() {
  const { status, user } = useSession();

  const [reportText, setReportText] = useState("HbA1c 7.2 LDL 4.1 BP 148/92");
  const [suggestionBusy, setSuggestionBusy] = useState(false);
  const [suggestionError, setSuggestionError] = useState<string | null>(null);
  const [suggestionResult, setSuggestionResult] = useState<SuggestionGenerateApiResponse | null>(null);

  const [scope, setScope] = useState<Scope>("self");
  const [overviewBusy, setOverviewBusy] = useState(false);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [mealRecords, setMealRecords] = useState<Array<Record<string, unknown>>>([]);
  const [suggestionItems, setSuggestionItems] = useState<SuggestionListApiResponse["items"]>([]);
  const [reminders, setReminders] = useState<ReminderEventView[]>([]);
  const [confirmationRate, setConfirmationRate] = useState(0);

  const [workflowsBusy, setWorkflowsBusy] = useState(false);
  const [workflowsError, setWorkflowsError] = useState<string | null>(null);
  const [workflowItems, setWorkflowItems] = useState<Array<Record<string, unknown>>>([]);
  const [selectedCorrelationId, setSelectedCorrelationId] = useState("");
  const [workflowDetail, setWorkflowDetail] = useState<WorkflowExecutionResult | null>(null);

  const [alertId, setAlertId] = useState("");
  const [alertBusy, setAlertBusy] = useState(false);
  const [alertError, setAlertError] = useState<string | null>(null);
  const [alertTimeline, setAlertTimeline] = useState<Array<Record<string, unknown>>>([]);

  async function runUnifiedSuggestionFlow() {
    setSuggestionBusy(true);
    setSuggestionError(null);
    try {
      const result = await generateSuggestionFromReport({ text: reportText });
      setSuggestionResult(result);
    } catch (error) {
      setSuggestionError(toErrorMessage(error));
    } finally {
      setSuggestionBusy(false);
    }
  }

  async function loadHouseholdAwareViews() {
    setOverviewBusy(true);
    setOverviewError(null);
    try {
      const [meals, suggestions, reminderState] = await Promise.all([
        listMealRecords(30),
        listSuggestions({ scope, limit: 30 }),
        listReminders(),
      ]);
      setMealRecords(meals.records);
      setSuggestionItems(suggestions.items);
      setReminders(reminderState.reminders);
      setConfirmationRate(reminderState.metrics.meal_confirmation_rate);
    } catch (error) {
      setOverviewError(toErrorMessage(error));
    } finally {
      setOverviewBusy(false);
    }
  }

  async function loadWorkflowList() {
    setWorkflowsBusy(true);
    setWorkflowsError(null);
    try {
      const data = await listWorkflows();
      setWorkflowItems(data.items);
      const firstCorrelation = data.items.find((item) => typeof item.correlation_id === "string")?.correlation_id;
      if (typeof firstCorrelation === "string") {
        setSelectedCorrelationId(firstCorrelation);
      }
    } catch (error) {
      setWorkflowsError(toErrorMessage(error));
    } finally {
      setWorkflowsBusy(false);
    }
  }

  async function loadSelectedWorkflow() {
    if (!selectedCorrelationId.trim()) return;
    setWorkflowsBusy(true);
    setWorkflowsError(null);
    try {
      const detail = await getWorkflow(selectedCorrelationId.trim());
      setWorkflowDetail(detail);
    } catch (error) {
      setWorkflowsError(toErrorMessage(error));
    } finally {
      setWorkflowsBusy(false);
    }
  }

  async function loadAlertTimeline() {
    if (!alertId.trim()) return;
    setAlertBusy(true);
    setAlertError(null);
    try {
      const data = await getAlertTimeline(alertId.trim());
      setAlertTimeline(data.outbox_timeline as Array<Record<string, unknown>>);
    } catch (error) {
      setAlertError(toErrorMessage(error));
    } finally {
      setAlertBusy(false);
    }
  }

  const trendBars = useMemo(() => {
    const today = new Date();
    const keys = Array.from({ length: 7 }, (_, idx) => {
      const d = new Date(today);
      d.setDate(today.getDate() - (6 - idx));
      return d.toISOString().slice(0, 10);
    });
    const counts = new Map<string, number>();
    for (const item of mealRecords) {
      const key = isoDay(item.captured_at ?? item.created_at);
      if (!key) continue;
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    const max = Math.max(1, ...keys.map((key) => counts.get(key) ?? 0));
    return keys.map((key) => {
      const count = counts.get(key) ?? 0;
      return {
        key,
        count,
        height: Math.max(10, Math.round((count / max) * 64)),
        label: key.slice(5),
      };
    });
  }, [mealRecords]);

  const reminderBreakdown = useMemo(() => {
    let yes = 0;
    let no = 0;
    let unknown = 0;
    for (const reminder of reminders) {
      const confirmation = reminder.meal_confirmation;
      if (confirmation === "yes") yes += 1;
      else if (confirmation === "no") no += 1;
      else unknown += 1;
    }
    return { yes, no, unknown };
  }, [reminders]);

  const dashboardError = status === "unauthenticated" ? "Sign in to use dashboard workflows." : null;

  return (
    <div>
      <PageTitle
        eyebrow="Overview"
        title="Daily Wellness Workspace"
        description="Unified operational dashboard for suggestions, household-aware reads, timeline inspection, and adherence trend monitoring."
        tags={["iteration target", "policy-ready", "live API"]}
      />

      {dashboardError ? <ErrorCard message={dashboardError} /> : null}

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Suggestions Unified Flow</CardTitle>
            <CardDescription>Run report parse + recommendation generation in one action and inspect typed output.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Label htmlFor="dashboard-report-text">Report text</Label>
            <Textarea
              id="dashboard-report-text"
              value={reportText}
              onChange={(event) => setReportText(event.target.value)}
              placeholder="Paste biomarker report text here..."
              className="min-h-[140px]"
            />
            <Button disabled={status !== "authenticated" || suggestionBusy || !reportText.trim()} onClick={runUnifiedSuggestionFlow}>
              {suggestionBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Generate Suggestion
            </Button>
            {suggestionError ? <ErrorCard message={suggestionError} /> : null}
            {suggestionResult ? (
              <div className="grid gap-2 sm:grid-cols-2">
                <div className="metric-card">
                  <div className="section-kicker">Safety Decision</div>
                  <div className="mt-1 text-sm font-semibold">{suggestionResult.suggestion.safety.decision}</div>
                </div>
                <div className="metric-card">
                  <div className="section-kicker">Suggestion ID</div>
                  <div className="mt-1 truncate text-sm font-semibold">{suggestionResult.suggestion.suggestion_id}</div>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Household-Aware Data Views</CardTitle>
            <CardDescription>Load meals, reminders, and suggestions under `self` or `household` scope.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-3 sm:grid-cols-[180px_1fr] sm:items-end">
              <div className="space-y-2">
                <Label htmlFor="dashboard-scope">Scope</Label>
                <Select id="dashboard-scope" value={scope} onChange={(event) => setScope(event.target.value as Scope)}>
                  <option value="self">Self</option>
                  <option value="household">Household</option>
                </Select>
              </div>
              <Button disabled={status !== "authenticated" || overviewBusy} onClick={loadHouseholdAwareViews}>
                {overviewBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Refresh Scope Data
              </Button>
            </div>
            {overviewError ? <ErrorCard message={overviewError} /> : null}
            <div className="grid gap-2 sm:grid-cols-3">
              <div className="metric-card">
                <div className="section-kicker">Meal Records</div>
                <div className="mt-1 text-lg font-semibold">{mealRecords.length}</div>
              </div>
              <div className="metric-card">
                <div className="section-kicker">Suggestions</div>
                <div className="mt-1 text-lg font-semibold">{suggestionItems.length}</div>
              </div>
              <div className="metric-card">
                <div className="section-kicker">Reminders</div>
                <div className="mt-1 text-lg font-semibold">{reminders.length}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-4 page-grid">
        <Card>
          <CardHeader>
            <CardTitle>Structured Timeline Viewers</CardTitle>
            <CardDescription>Inspect workflow timelines and alert outbox events using correlation and alert IDs.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap gap-2">
              <Button disabled={status !== "authenticated" || workflowsBusy} onClick={loadWorkflowList}>
                {workflowsBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Load Workflows
              </Button>
              <Button variant="secondary" disabled={status !== "authenticated" || workflowsBusy || !selectedCorrelationId} onClick={loadSelectedWorkflow}>
                Open Selected Workflow
              </Button>
            </div>
            {workflowItems.length > 0 ? (
              <Select value={selectedCorrelationId} onChange={(event) => setSelectedCorrelationId(event.target.value)}>
                {workflowItems.map((item) => {
                  const correlationId = typeof item.correlation_id === "string" ? item.correlation_id : "";
                  const workflowName = typeof item.workflow_name === "string" ? item.workflow_name : "workflow";
                  if (!correlationId) return null;
                  return (
                    <option key={correlationId} value={correlationId}>
                      {workflowName} :: {correlationId}
                    </option>
                  );
                })}
              </Select>
            ) : null}
            {workflowsError ? <ErrorCard message={workflowsError} /> : null}
            {workflowDetail?.timeline_events ? (
              <div className="data-list">
                {workflowDetail.timeline_events.slice(0, 8).map((event, idx) => (
                  <div key={`${String(event.event_type)}-${idx}`} className="data-list-row">
                    <div className="text-sm font-semibold">{String(event.event_type ?? "event")}</div>
                    <div className="app-muted text-xs">{String(event.created_at ?? "")}</div>
                  </div>
                ))}
              </div>
            ) : null}

            <Separator />

            <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
              <div className="space-y-2">
                <Label htmlFor="dashboard-alert-id">Alert ID</Label>
                <Input
                  id="dashboard-alert-id"
                  value={alertId}
                  onChange={(event) => setAlertId(event.target.value)}
                  placeholder="alert_..."
                />
              </div>
              <Button disabled={status !== "authenticated" || alertBusy || !alertId.trim()} onClick={loadAlertTimeline}>
                {alertBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Load Alert Timeline
              </Button>
            </div>
            {alertError ? <ErrorCard message={alertError} /> : null}
            {alertTimeline.length > 0 ? (
              <div className="data-list">
                {alertTimeline.slice(0, 6).map((event, idx) => (
                  <div key={`${String(event.state ?? event.event_type)}-${idx}`} className="data-list-row">
                    <div className="text-sm font-semibold">{String(event.state ?? event.event_type ?? "event")}</div>
                    <div className="app-muted text-xs">{String(event.created_at ?? "")}</div>
                  </div>
                ))}
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Adherence and Confirmation Trends</CardTitle>
            <CardDescription>Simple operational charting from live reminders and meal capture data.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="metric-card">
              <div className="section-kicker">Meal Confirmation Rate</div>
              <div className="mt-1 text-2xl font-semibold">{Math.round(confirmationRate * 100)}%</div>
            </div>

            <div className="grid gap-2 sm:grid-cols-3">
              <div className="metric-card">
                <div className="section-kicker">Yes</div>
                <div className="mt-1 text-lg font-semibold">{reminderBreakdown.yes}</div>
              </div>
              <div className="metric-card">
                <div className="section-kicker">No</div>
                <div className="mt-1 text-lg font-semibold">{reminderBreakdown.no}</div>
              </div>
              <div className="metric-card">
                <div className="section-kicker">Unknown</div>
                <div className="mt-1 text-lg font-semibold">{reminderBreakdown.unknown}</div>
              </div>
            </div>

            <div className="metric-card">
              <div className="section-kicker mb-3">7-Day Meal Capture</div>
              <div className="flex items-end justify-between gap-2">
                {trendBars.map((bar) => (
                  <div key={bar.key} className="flex flex-1 flex-col items-center gap-1">
                    <div className="w-full rounded-md bg-[color:var(--accent)]/15">
                      <div
                        className="mx-auto rounded-md bg-[color:var(--accent)]"
                        style={{ height: `${bar.height}px`, width: "80%" }}
                      />
                    </div>
                    <div className="text-[11px] text-[color:var(--muted-foreground)]">{bar.label}</div>
                    <div className="text-xs font-medium">{bar.count}</div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          ["Meal Analysis", "Upload photos, inspect summaries, and review saved records.", "/meals"],
          ["Reminders", "Generate events and confirm meals with metrics feedback.", "/reminders"],
          ["Suggestions", "Parse report text and generate persisted suggestions.", "/suggestions"],
          ["Household", "Create a family-like group and manage invites/members.", "/household"],
        ].map(([title, text, href]) => (
          <Card key={title}>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">{title}</CardTitle>
              <CardDescription>{text}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild size="sm" variant="secondary">
                <Link href={String(href)}>Open</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="mt-3 app-muted text-xs">Signed in as: {user ? `${user.display_name} (${user.account_role})` : "anonymous"}</div>
    </div>
  );
}
