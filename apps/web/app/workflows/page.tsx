"use client";

import { useEffect, useMemo, useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { JsonViewer } from "@/components/app/json-viewer";
import { PageTitle } from "@/components/app/page-title";
import { TimelineList, type TimelineListItem } from "@/components/app/timeline-list";
import { useSession } from "@/components/app/session-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getWorkflow, listWorkflows } from "@/lib/api/workflow-client";
import type { WorkflowExecutionResult, WorkflowListApiResponse } from "@/lib/types";

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
        subtitle: `${event.created_at} • ${event.workflow_name ?? "unknown"}`,
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
    <div>
      <PageTitle eyebrow="Workflows" title="Workflow Trace Inspector" description="List workflow traces and replay a correlation timeline." />

      <div className="page-grid">
        <div className="space-y-4">
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
                  const firstCorrelationId = data.items[0]?.correlation_id ?? "";
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

            <Input
              value={correlationId}
              placeholder="correlation_id"
              onChange={(e) => setCorrelationId(e.target.value)}
              className="max-w-sm"
            />

            <Button
              variant="secondary"
              disabled={loadingAction !== null || !canFetch || !correlationId}
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
              <AsyncLabel active={loadingAction === "fetch"} loading="Fetching" idle="Fetch" />
            </Button>
          </div>

          {error ? <ErrorCard title="Workflow error" message={error} /> : null}
        </div>

        <TimelineList title="Workflow Runs" description="Latest traces first" items={workflowListItems} emptyLabel="List workflows to inspect trace runs." />

        <TimelineList
          title="Timeline Events"
          description={result ? `${result.timeline_events.length} events` : undefined}
          items={timelineItems}
          emptyLabel="Fetch a correlation id to view the workflow trace."
        />

        <JsonViewer title="Workflow Execution Result" data={result} emptyLabel="Fetch a correlation id to inspect the trace payload." />
      </div>
    </div>
  );
}

