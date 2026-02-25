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
          <JsonViewer title="Workflow List" data={listResult} emptyLabel="List workflows to browse recent traces." />
          <JsonViewer title="Workflow Trace" data={result} emptyLabel="Fetch a workflow by correlation ID to inspect timeline events." />
        </div>
      </div>
    </div>
  );
}
