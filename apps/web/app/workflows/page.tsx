"use client";

import { useState } from "react";
import { useEffect } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { JsonViewer } from "@/components/app/json-viewer";
import { PageTitle } from "@/components/app/page-title";
import { TimelineList } from "@/components/app/timeline-list";
import { useSession } from "@/components/app/session-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getWorkflow, listWorkflows } from "@/lib/api";

export default function WorkflowsPage() {
  const { hasScope, status } = useSession();
  const [correlationId, setCorrelationId] = useState("");
  const [queryCorrelationId, setQueryCorrelationId] = useState("");
  const [result, setResult] = useState<object | null>(null);
  const [listResult, setListResult] = useState<object | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<"list" | "fetch" | null>(null);
  const workflowItems = ((listResult as { items?: Array<Record<string, unknown>> } | null)?.items ?? []) as Array<
    Record<string, unknown>
  >;
  const traceEventCount =
    ((result as { timeline_events?: Array<Record<string, unknown>> } | null)?.timeline_events?.length ?? null) as
      | number
      | null;
  const traceEvents = ((result as { timeline_events?: Array<Record<string, unknown>> } | null)?.timeline_events ??
    []) as Array<Record<string, unknown>>;
  const canList = status === "authenticated" && hasScope("workflow:read");
  const canFetch = status === "authenticated" && hasScope("workflow:replay");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const corr = params.get("correlation_id") ?? "";
    if (corr) setQueryCorrelationId(corr);
  }, []);

  useEffect(() => {
    if (queryCorrelationId && queryCorrelationId !== correlationId) {
      setCorrelationId(queryCorrelationId);
    }
  }, [queryCorrelationId, correlationId]);

  useEffect(() => {
    if (!queryCorrelationId || !canFetch) return;
    let cancelled = false;
    const run = async () => {
      setError(null);
      setLoadingAction("fetch");
      try {
        const workflow = await getWorkflow(queryCorrelationId);
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
  }, [queryCorrelationId, canFetch]);

  return (
    <div>
      <PageTitle
        eyebrow="Workflows"
        title="Workflow Trace Inspector"
        description="List workflow traces and replay a specific correlation timeline. This page exercises both the collection and detail read endpoints."
        tags={["admin scope", "workflow:read", "workflow:replay"]}
      />

      <div className="page-grid">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Workflow Lookup</CardTitle>
            <CardDescription>
              Use the collection route first, then replay a specific correlation timeline.
              {queryCorrelationId ? ` Query prefill: ${queryCorrelationId}` : ""}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!canList || !canFetch ? (
              <div className="rounded-xl border border-dashed border-[color:var(--border)] bg-white/40 p-3 text-sm text-[color:var(--muted-foreground)] dark:bg-[color:var(--panel-soft)]/70">
                Admin scopes required:
                {!canList ? " `workflow:read`" : ""}
                {!canFetch ? " `workflow:replay`" : ""}.
              </div>
            ) : null}
            <div className="flex flex-wrap gap-2">
              <Button
                disabled={loadingAction !== null || !canList}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("list");
                  try {
                    const data = await listWorkflows();
                    setListResult(data);
                    const firstCorrelationId = (data.items?.[0]?.correlation_id as string | undefined) ?? "";
                    if (firstCorrelationId) setCorrelationId(firstCorrelationId);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "list"} loading="Loading" idle="List Workflows" />
              </Button>
            </div>
            <div className="space-y-2">
              <label htmlFor="workflow-correlation-id" className="text-sm font-medium">
                Correlation ID
              </label>
              <Input
                id="workflow-correlation-id"
                placeholder="corr_abc123…"
                value={correlationId}
                onChange={(e) => setCorrelationId(e.target.value)}
              />
            </div>
            <Button
              variant="secondary"
              disabled={!correlationId || loadingAction !== null || !canFetch}
              onClick={async () => {
                try {
                  setError(null);
                  setLoadingAction("fetch");
                  setResult(await getWorkflow(correlationId));
                } catch (e) {
                  setError(e instanceof Error ? e.message : String(e));
                } finally {
                  setLoadingAction(null);
                }
              }}
            >
              <AsyncLabel active={loadingAction === "fetch"} loading="Fetching" idle="Fetch Workflow" />
            </Button>
          </CardContent>
        </Card>

        <div className="stack-grid">
          {error ? <ErrorCard message={error} /> : null}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Trace Overview</CardTitle>
              <CardDescription>Recent workflow inventory and selected trace status.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Listed Workflows</div>
                  <div className="mt-1 text-sm font-medium">{workflowItems.length || "None loaded"}</div>
                </div>
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Selected Trace Events</div>
                  <div className="mt-1 text-sm font-medium">{traceEventCount ?? "No trace loaded"}</div>
                </div>
              </div>
              {workflowItems.length > 0 ? (
                <div className="data-list mt-3">
                  {workflowItems.slice(0, 3).map((item, idx) => (
                    <div key={String(item.correlation_id ?? idx)} className="data-list-row">
                      <div className="text-sm font-medium">{String(item.workflow_name ?? "workflow")}</div>
                      <div className="app-muted text-xs break-all">{String(item.correlation_id ?? "unknown")}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </CardContent>
          </Card>
          <TimelineList
            title="Recent Workflows"
            description="Structured list view for the latest workflow traces."
            items={workflowItems.slice(0, 8).map((item, idx) => ({
              id: String(item.correlation_id ?? idx),
              title: String(item.workflow_name ?? "workflow"),
              subtitle: String(item.correlation_id ?? "unknown"),
              badges: [String(item.status ?? "trace")],
              onClick: () => {
                const nextId = String(item.correlation_id ?? "");
                if (nextId) setCorrelationId(nextId);
              },
            }))}
            emptyLabel="List workflows to populate the structured trace browser."
          />
          <TimelineList
            title="Timeline Preview"
            description="Step-by-step events from the selected workflow trace."
            items={traceEvents.slice(0, 12).map((event, idx) => ({
              id: String(event.event_id ?? idx),
              title: String(event.event_name ?? event.node_name ?? event.stage ?? event.event_type ?? "event"),
              subtitle: String(event.timestamp ?? event.created_at ?? "No timestamp"),
              badges: "severity" in event ? [String(event.severity)] : [],
            }))}
            emptyLabel="Fetch a workflow to preview trace events."
          />
          <JsonViewer title="Workflow List" data={listResult} emptyLabel="List workflows to browse recent traces." />
          <JsonViewer title="Workflow Trace" data={result} emptyLabel="Fetch a workflow by correlation ID to inspect timeline events." />
        </div>
      </div>
    </div>
  );
}
