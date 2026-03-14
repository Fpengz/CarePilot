"use client";

import { useEffect, useMemo, useState } from "react";
import { Workflow, History, Search, Terminal, Activity, FileJson } from "lucide-react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { JsonViewer } from "@/components/app/json-viewer";
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
    <div className="section-stack">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 text-indigo-600">
          <Workflow className="h-5 w-5" />
          <span className="text-[10px] font-bold uppercase tracking-[0.2em]">Administrative Audit</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight">Workflow Intelligence</h1>
        <p className="text-[color:var(--muted-foreground)] leading-relaxed max-w-2xl text-sm">
          Trace the execution lifecycle of AI-driven events, replay correlation timelines, and inspect raw event payloads.
        </p>
      </div>

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
              <div className="flex flex-col gap-4 sm:flex-row">
                <div className="flex-1 space-y-2">
                  <Label htmlFor="corr-id" className="text-[10px] font-bold uppercase tracking-widest opacity-70">Correlation ID</Label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[color:var(--muted-foreground)] opacity-50" />
                    <Input
                      id="corr-id"
                      value={correlationId}
                      onChange={(e) => setCorrelationId(e.target.value)}
                      placeholder="Enter correlation_id..."
                      className="h-11 rounded-xl pl-10"
                    />
                  </div>
                </div>
                <div className="flex items-end gap-2">
                  <Button
                    variant="outline"
                    className="h-11 rounded-xl font-bold px-6"
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
                    className="h-11 rounded-xl font-bold px-8 shadow-sm"
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
            <JsonViewer title="Execution Context Result" data={result} emptyLabel="Search a correlation to inspect the trace payload." />
          </div>
        </div>

        <div className="space-y-8 lg:sticky lg:top-28">
          <div className="clinical-card bg-indigo-500/[0.03] border-indigo-500/10">
            <div className="flex items-center gap-2 text-indigo-600 mb-4">
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
