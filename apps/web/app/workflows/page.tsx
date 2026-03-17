"use client";

import { useEffect, useMemo, useState } from "react";
import { Workflow, History, Search, Terminal, Activity, FileJson } from "lucide-react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { TimelineList, type TimelineListItem } from "@/components/app/timeline-list";
import { useSession } from "@/components/app/session-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getWorkflow, listWorkflows } from "@/lib/api/workflow-client";
import type { WorkflowExecutionResult, WorkflowListApiResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function WorkflowsPage() {
  const { hasScope, status } = useSession();
  const [queryCorrelationId, setQueryCorrelationId] = useState("");
  const [correlationId, setCorrelationId] = useState("");
  const [result, setResult] = useState<WorkflowExecutionResult | null>(null);
  const [listResult, setListResult] = useState<WorkflowListApiResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<"list" | "fetch" | null>(null);

  const canList = status === "authenticated" && hasScope("workflow:read");
  const canFetch = status === "authenticated" && hasScope("workflow:replay");

  const workflowListItems: TimelineListItem[] = useMemo(
    () =>
      (listResult?.items ?? []).map((item) => ({
        id: item.correlation_id,
        title: item.workflow_name ?? "workflow",
        subtitle: item.correlation_id,
        badges: [`events:${item.event_count}`],
        onClick: () => setCorrelationId(item.correlation_id),
      })),
    [listResult]
  );

  const timelineItems: TimelineListItem[] = useMemo(
    () =>
      (result?.timeline_events ?? []).map((event) => ({
        id: event.event_id,
        title: event.event_type,
        subtitle: `${new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(event.created_at))} • ${event.workflow_name ?? "unknown"}`,
      })),
    [result]
  );

  const formatTimestamp = (value?: string | null) => {
    if (!value) return "Unknown time";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(
      date
    );
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const corr = params.get("correlation_id") ?? "";
    if (corr) setQueryCorrelationId(corr);
  }, []);

  useEffect(() => {
    if (queryCorrelationId && queryCorrelationId !== correlationId) setCorrelationId(queryCorrelationId);
  }, [queryCorrelationId, correlationId]);

  useEffect(() => {
    if (!correlationId || !canFetch) return;
    let cancelled = false;
    const run = async () => {
      setError(null);
      setLoadingAction("fetch");
      try {
        const workflow = await getWorkflow(correlationId);
        if (!cancelled) setResult(workflow);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoadingAction(null);
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [correlationId, canFetch]);

  return (
    <div className="section-stack max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
      <PageTitle
        eyebrow="Administrative Audit"
        title="Workflow Intelligence"
        description="Trace the execution lifecycle of AI-driven events, replay correlation timelines, and inspect raw event payloads."
        tags={["Operational telemetry", "Secure replay"]}
      />

      {!canList || !canFetch ? (
        <div className="rounded-xl border border-dashed border-indigo-200 bg-indigo-50/50 p-4 text-sm text-indigo-800">
          <p className="font-bold flex items-center gap-2 mb-1">
            <Terminal className="h-4 w-4" /> Privileged Access Required
          </p>
          <p className="opacity-80">Admin scopes required: {!canList ? "[workflow:read] " : ""}{!canFetch ? "[workflow:replay]" : ""}</p>
        </div>
      ) : null}

      <div className="page-grid items-start">
        <div className="space-y-8">
          <div className="clinical-card space-y-8">
            <div className="space-y-1">
              <h3 className="clinical-subtitle">Trace Inspector</h3>
              <p className="clinical-body">Search for specific event correlations or browse recent executions.</p>
            </div>

            <div className="space-y-6">
              <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
                <div className="space-y-2">
                  <Label htmlFor="corr-id" className="text-[10px] font-bold uppercase tracking-widest opacity-70">
                    Correlation ID
                  </Label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[color:var(--muted-foreground)] opacity-50" />
                    <Input
                      id="corr-id"
                      value={correlationId}
                      onChange={(e) => setCorrelationId(e.target.value)}
                      placeholder="Enter correlation_id..."
                      className="h-12 rounded-xl pl-10"
                    />
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    variant="secondary"
                    className="h-12 rounded-xl font-bold px-6"
                    disabled={loadingAction !== null || !canList}
                    onClick={async () => {
                      setError(null);
                      setLoadingAction("list");
                      try {
                        const data = await listWorkflows();
                        setListResult(data);
                      } catch (e) {
                        setError(e instanceof Error ? e.message : String(e));
                      } finally {
                        setLoadingAction(null);
                      }
                    }}
                  >
                    <AsyncLabel active={loadingAction === "list"} loading="Listing" idle="Recent Runs" />
                  </Button>
                  <Button
                    className="h-12 rounded-xl font-bold px-8 shadow-sm"
                    disabled={!correlationId || loadingAction !== null || !canFetch}
                    onClick={async () => {
                      setError(null);
                      setLoadingAction("fetch");
                      try {
                        setResult(await getWorkflow(correlationId));
                      } catch (e) {
                        setError(e instanceof Error ? e.message : String(e));
                      } finally {
                        setLoadingAction(null);
                      }
                    }}
                  >
                    <AsyncLabel active={loadingAction === "fetch"} loading="Replaying" idle="Trace" />
                  </Button>
                </div>
              </div>

              {error && <ErrorCard title="Trace Error" message={error} />}
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <FileJson className="h-4 w-4 text-[color:var(--muted-foreground)]" />
              <h4 className="text-xs font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Replay Details</h4>
            </div>
            {result ? (
              <div className="grid gap-4">
                <div className="clinical-card space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h3 className="clinical-subtitle">Execution Summary</h3>
                      <p className="clinical-body">Human-readable replay metadata and identifiers.</p>
                    </div>
                    <span className="rounded-full border border-[color:var(--border-soft)] bg-[color:var(--panel-soft)] px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">
                      {result.replayed ? "Replayed" : "Live"}
                    </span>
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] px-4 py-3">
                      <div className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">
                        Workflow Name
                      </div>
                      <div className="mt-2 text-sm font-semibold">{result.workflow_name}</div>
                    </div>
                    <div className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] px-4 py-3">
                      <div className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">
                        Request ID
                      </div>
                      <div className="mt-2 text-xs font-mono break-all">{result.request_id}</div>
                    </div>
                    <div className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] px-4 py-3">
                      <div className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">
                        Correlation ID
                      </div>
                      <div className="mt-2 text-xs font-mono break-all">{result.correlation_id}</div>
                    </div>
                    <div className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] px-4 py-3">
                      <div className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">
                        Event Count
                      </div>
                      <div className="mt-2 text-sm font-semibold">
                        {result.timeline_events.length}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="clinical-card space-y-5">
                  <div className="space-y-1">
                    <h3 className="clinical-subtitle">Event Payloads</h3>
                    <p className="clinical-body">Each workflow step with structured payload context.</p>
                  </div>
                  <div className="space-y-3">
                    {result.timeline_events.map((event) => (
                      <div
                        key={event.event_id}
                        className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] px-4 py-4 shadow-[0_4px_16px_rgba(15,23,42,0.04)]"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div>
                            <div className="text-xs font-semibold uppercase tracking-widest text-[color:var(--muted-foreground)]">
                              {event.event_type}
                            </div>
                            <div className="mt-1 text-sm font-semibold">{event.workflow_name ?? "workflow"}</div>
                          </div>
                          <div className="text-xs text-[color:var(--muted-foreground)]">
                            {formatTimestamp(event.created_at)}
                          </div>
                        </div>
                        {event.payload && Object.keys(event.payload).length > 0 ? (
                          <div className="mt-3 grid gap-2">
                            {Object.entries(event.payload).map(([key, value]) => (
                              <div
                                key={`${event.event_id}-${key}`}
                                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[color:var(--border-soft)] bg-[color:var(--panel-soft)] px-3 py-2 text-xs"
                              >
                                <span className="font-semibold uppercase tracking-widest text-[color:var(--muted-foreground)]">
                                  {key.replace(/_/g, " ")}
                                </span>
                                <span className="font-mono text-[color:var(--foreground)]">
                                  {typeof value === "string" ? value : JSON.stringify(value)}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="mt-3 text-xs text-[color:var(--muted-foreground)] italic">
                            No payload fields recorded for this event.
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-[color:var(--border)] bg-white/40 p-4 text-sm text-[color:var(--muted-foreground)] dark:bg-[color:var(--panel-soft)]/70">
                Search a correlation to inspect the trace payload.
              </div>
            )}
          </div>
        </div>

        <div className="space-y-8 lg:sticky lg:top-24">
          <div className="clinical-card bg-indigo-500/[0.03] border-indigo-500/10 space-y-4">
            <div className="flex items-center gap-2 text-indigo-600">
              <Activity className="h-4 w-4" />
              <span className="text-[10px] font-bold uppercase tracking-widest">Active Session</span>
            </div>
            <div className="grid gap-4">
              <div className="space-y-1">
                <div className="text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)] opacity-70">Event Count</div>
                <div className="text-xl font-bold">{result?.timeline_events.length ?? 0}</div>
              </div>
              <div className="space-y-1">
                <div className="text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)] opacity-70">Current Context</div>
                <div className="text-xs font-mono truncate">{correlationId || "Waiting for ID"}</div>
              </div>
            </div>
          </div>

          <TimelineList
            title="Correlation History"
            description="Recent workflow traces"
            items={workflowListItems}
            emptyLabel="Wait for recent list..."
          />

          <TimelineList
            title="Execution Timeline"
            description={result ? `Replay of ${result.timeline_events.length} steps` : "Event sequence"}
            items={timelineItems}
            emptyLabel="Waiting for trace..."
          />
        </div>
      </div>
    </div>
  );
}
