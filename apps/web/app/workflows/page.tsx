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
import {
  compareWorkflowContractSnapshots,
  createWorkflowContractSnapshot,
  createWorkflowToolPolicy,
  evaluateWorkflowToolPolicy,
  getWorkflow,
  getWorkflowRuntimeContract,
  listWorkflowContractSnapshots,
  listWorkflowToolPolicies,
  listWorkflows,
  patchWorkflowToolPolicy,
} from "@/lib/api";
import type {
  ToolPolicyEvaluationApiResponse,
  ToolPolicyListApiResponse,
  WorkflowExecutionResult,
  WorkflowListApiResponse,
  WorkflowRuntimeRegistryApiResponse,
  WorkflowSnapshotCompareApiResponse,
  WorkflowSnapshotListApiResponse,
} from "@/lib/types";

export default function WorkflowsPage() {
  const { hasScope, status } = useSession();
  const [correlationId, setCorrelationId] = useState("");
  const [queryCorrelationId, setQueryCorrelationId] = useState("");
  const [result, setResult] = useState<WorkflowExecutionResult | null>(null);
  const [listResult, setListResult] = useState<WorkflowListApiResponse | null>(null);
  const [runtimeContract, setRuntimeContract] = useState<WorkflowRuntimeRegistryApiResponse | null>(null);
  const [snapshotList, setSnapshotList] = useState<WorkflowSnapshotListApiResponse | null>(null);
  const [snapshotCompare, setSnapshotCompare] = useState<WorkflowSnapshotCompareApiResponse | null>(null);
  const [toolPolicyList, setToolPolicyList] = useState<ToolPolicyListApiResponse | null>(null);
  const [toolPolicyEval, setToolPolicyEval] = useState<ToolPolicyEvaluationApiResponse | null>(null);
  const [policyRole, setPolicyRole] = useState<"member" | "admin">("admin");
  const [policyAgentId, setPolicyAgentId] = useState("notification_agent");
  const [policyToolName, setPolicyToolName] = useState("trigger_alert");
  const [policyEffect, setPolicyEffect] = useState<"allow" | "deny">("deny");
  const [policyEnvironment, setPolicyEnvironment] = useState("dev");
  const [error, setError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<
    "list" | "fetch" | "runtime" | "snapshots" | "create-snapshot" | "policies" | "policy-create" | "policy-eval" | null
  >(null);
  const workflowItems = listResult?.items ?? [];
  const traceEvents = result?.timeline_events ?? [];
  const traceEventCount = result ? traceEvents.length : null;
  const canList = status === "authenticated" && hasScope("workflow:read");
  const canFetch = status === "authenticated" && hasScope("workflow:replay");
  const canWrite = status === "authenticated" && hasScope("workflow:write");

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
              <Button
                variant="ghost"
                disabled={loadingAction !== null || !canList}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("runtime");
                  try {
                    setRuntimeContract(await getWorkflowRuntimeContract());
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "runtime"} loading="Loading" idle="Load Runtime Contract" />
              </Button>
              <Button
                variant="ghost"
                disabled={loadingAction !== null || !canList}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("snapshots");
                  try {
                    const snapshots = await listWorkflowContractSnapshots();
                    setSnapshotList(snapshots);
                    if (snapshots.items.length >= 2) {
                      const base = snapshots.items[1]?.version;
                      const target = snapshots.items[0]?.version;
                      if (typeof base === "number" && typeof target === "number") {
                        setSnapshotCompare(await compareWorkflowContractSnapshots(base, target));
                      }
                    }
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "snapshots"} loading="Loading" idle="Load Snapshots" />
              </Button>
              <Button
                variant="ghost"
                disabled={loadingAction !== null || !canWrite}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("create-snapshot");
                  try {
                    await createWorkflowContractSnapshot();
                    setSnapshotList(await listWorkflowContractSnapshots());
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "create-snapshot"} loading="Creating" idle="Create Snapshot" />
              </Button>
              <Button
                variant="ghost"
                disabled={loadingAction !== null || !canList}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("policies");
                  try {
                    setToolPolicyList(await listWorkflowToolPolicies());
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "policies"} loading="Loading" idle="Load Tool Policies" />
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
            <div className="grid gap-2 sm:grid-cols-2">
              <Input
                aria-label="Policy role"
                value={policyRole}
                onChange={(e) => setPolicyRole((e.target.value === "member" ? "member" : "admin"))}
                placeholder="admin or member"
              />
              <Input
                aria-label="Policy effect"
                value={policyEffect}
                onChange={(e) => setPolicyEffect((e.target.value === "allow" ? "allow" : "deny"))}
                placeholder="allow or deny"
              />
              <Input
                aria-label="Policy agent id"
                value={policyAgentId}
                onChange={(e) => setPolicyAgentId(e.target.value)}
                placeholder="agent_id"
              />
              <Input
                aria-label="Policy tool name"
                value={policyToolName}
                onChange={(e) => setPolicyToolName(e.target.value)}
                placeholder="tool_name"
              />
              <Input
                aria-label="Policy environment"
                value={policyEnvironment}
                onChange={(e) => setPolicyEnvironment(e.target.value)}
                placeholder="environment"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                disabled={loadingAction !== null || !canWrite || !policyAgentId || !policyToolName}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("policy-create");
                  try {
                    const created = await createWorkflowToolPolicy({
                      role: policyRole,
                      agent_id: policyAgentId,
                      tool_name: policyToolName,
                      effect: policyEffect,
                      conditions: { environment: policyEnvironment || "dev" },
                      priority: 100,
                      enabled: true,
                    });
                    const latest = await listWorkflowToolPolicies();
                    setToolPolicyList(latest);
                    setToolPolicyEval(
                      await evaluateWorkflowToolPolicy({
                        role: created.policy.role,
                        agent_id: created.policy.agent_id,
                        tool_name: created.policy.tool_name,
                        environment: policyEnvironment || "dev",
                      }),
                    );
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "policy-create"} loading="Creating" idle="Create Policy" />
              </Button>
              <Button
                variant="secondary"
                disabled={loadingAction !== null || !canList || !policyAgentId || !policyToolName}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("policy-eval");
                  try {
                    setToolPolicyEval(
                      await evaluateWorkflowToolPolicy({
                        role: policyRole,
                        agent_id: policyAgentId,
                        tool_name: policyToolName,
                        environment: policyEnvironment || "dev",
                      }),
                    );
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "policy-eval"} loading="Evaluating" idle="Evaluate Policy" />
              </Button>
              <Button
                variant="ghost"
                disabled={loadingAction !== null || !canWrite}
                onClick={async () => {
                  try {
                    setError(null);
                    const list = toolPolicyList?.items ?? [];
                    const firstEnabled = list.find((item) => item.enabled === true);
                    const target = firstEnabled ?? list[0];
                    const policyId = target?.id ?? "";
                    if (!policyId) return;
                    await patchWorkflowToolPolicy(policyId, { enabled: false });
                    setToolPolicyList(await listWorkflowToolPolicies());
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  }
                }}
              >
                Disable First Policy
              </Button>
            </div>
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
                    <div key={item.correlation_id || String(idx)} className="data-list-row">
                      <div className="text-sm font-medium">{item.workflow_name ?? "workflow"}</div>
                      <div className="app-muted text-xs break-all">{item.correlation_id || "unknown"}</div>
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
              id: item.correlation_id || String(idx),
              title: item.workflow_name ?? "workflow",
              subtitle: item.correlation_id || "unknown",
              badges: [String(item.event_count)],
              onClick: () => {
                const nextId = item.correlation_id ?? "";
                if (nextId) setCorrelationId(nextId);
              },
            }))}
            emptyLabel="List workflows to populate the structured trace browser."
          />
          <TimelineList
            title="Timeline Preview"
            description="Step-by-step events from the selected workflow trace."
            items={traceEvents.slice(0, 12).map((event, idx) => ({
              id: event.event_id || String(idx),
              title: event.event_type || "event",
              subtitle: event.created_at || "No timestamp",
              badges: [event.workflow_name ?? "timeline"],
            }))}
            emptyLabel="Fetch a workflow to preview trace events."
          />
          <JsonViewer title="Workflow List" data={listResult} emptyLabel="List workflows to browse recent traces." />
          <JsonViewer title="Workflow Trace" data={result} emptyLabel="Fetch a workflow by correlation ID to inspect timeline events." />
          <JsonViewer
            title="Runtime Contract"
            data={runtimeContract}
            emptyLabel="Load runtime contract to inspect workflow-agent capabilities and tools."
          />
          <JsonViewer
            title="Runtime Contract Snapshots"
            data={snapshotList}
            emptyLabel="Load snapshots to inspect runtime contract versions."
          />
          <JsonViewer
            title="Snapshot Comparison"
            data={snapshotCompare}
            emptyLabel="Load snapshots to compare the latest two versions."
          />
          <JsonViewer title="Tool Policies" data={toolPolicyList} emptyLabel="Load tool policies for governance inspection." />
          <JsonViewer
            title="Tool Policy Evaluation"
            data={toolPolicyEval}
            emptyLabel="Evaluate a role/agent/tool policy decision."
          />
        </div>
      </div>
    </div>
  );
}
