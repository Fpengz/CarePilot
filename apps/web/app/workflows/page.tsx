"use client";

import { useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { JsonViewer } from "@/components/app/json-viewer";
import { PageTitle } from "@/components/app/page-title";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getWorkflow, listWorkflows } from "@/lib/api";

export default function WorkflowsPage() {
  const [correlationId, setCorrelationId] = useState("");
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
            <CardDescription>Use the collection route first, then replay a specific correlation timeline.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <Button
                disabled={loadingAction !== null}
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
              disabled={!correlationId || loadingAction !== null}
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
          <JsonViewer title="Workflow List" data={listResult} emptyLabel="List workflows to browse recent traces." />
          <JsonViewer title="Workflow Trace" data={result} emptyLabel="Fetch a workflow by correlation ID to inspect timeline events." />
        </div>
      </div>
    </div>
  );
}
