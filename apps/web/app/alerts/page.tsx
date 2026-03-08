"use client";

import { useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { JsonViewer } from "@/components/app/json-viewer";
import { PageTitle } from "@/components/app/page-title";
import { TimelineList } from "@/components/app/timeline-list";
import { useSession } from "@/components/app/session-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getAlertTimeline, triggerAlert } from "@/lib/api/workflow-client";

export default function AlertsPage() {
  const { hasScope, status } = useSession();
  const [result, setResult] = useState<object | null>(null);
  const [timelineResult, setTimelineResult] = useState<object | null>(null);
  const [alertId, setAlertId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<"trigger" | "timeline" | null>(null);
  const triggeredAlertId =
    ((result as { tool_result?: { output?: { alert_id?: string } } } | null)?.tool_result?.output?.alert_id as
      | string
      | undefined) ?? null;
  const timelineCount = ((timelineResult as { outbox_timeline?: unknown[] } | null)?.outbox_timeline?.length ??
    null) as number | null;
  const outboxTimeline = ((timelineResult as { outbox_timeline?: Array<Record<string, unknown>> } | null)
    ?.outbox_timeline ?? []) as Array<Record<string, unknown>>;
  const triggerWorkflowTimeline = ((result as { workflow?: { timeline_events?: Array<Record<string, unknown>> } } | null)
    ?.workflow?.timeline_events ?? []) as Array<Record<string, unknown>>;
  const canTrigger = status === "authenticated" && hasScope("alert:trigger");
  const canReadTimeline = status === "authenticated" && hasScope("alert:timeline:read");

  return (
    <div>
      <PageTitle
        eyebrow="Alerts"
        title="Privileged Alert Trigger and Timeline"
        description="Admin-scoped operation for triggering alerts and inspecting the outbox timeline read endpoint."
        tags={["admin scope", "alert:trigger", "alert:timeline:read"]}
      />

      <div className="page-grid">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Alert Operations</CardTitle>
            <CardDescription>These actions require admin scopes and are expected to fail with 403 for member accounts.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!canTrigger || !canReadTimeline ? (
              <div className="rounded-xl border border-dashed border-[color:var(--border)] bg-white/40 p-3 text-sm text-[color:var(--muted-foreground)] dark:bg-[color:var(--panel-soft)]/70">
                Admin scopes required:
                {!canTrigger ? " `alert:trigger`" : ""}
                {!canReadTimeline ? " `alert:timeline:read`" : ""}.
              </div>
            ) : null}
            <Button
              disabled={loadingAction !== null || !canTrigger}
              onClick={async () => {
                setError(null);
                setResult(null);
                setLoadingAction("trigger");
                try {
                  const data = await triggerAlert({
                    alert_type: "manual_test_alert",
                    severity: "warning",
                    message: "Manual end-to-end alert verification",
                    destinations: ["in_app"],
                  });
                  setResult(data);
                  const maybeAlertId =
                    ((data.tool_result?.output as { alert_id?: string } | undefined)?.alert_id as string | undefined) ??
                    "";
                  if (maybeAlertId) setAlertId(maybeAlertId);
                } catch (e) {
                  setError(e instanceof Error ? e.message : String(e));
                } finally {
                  setLoadingAction(null);
                }
              }}
            >
              <AsyncLabel active={loadingAction === "trigger"} loading="Triggering" idle="Trigger Alert" />
            </Button>

            <div className="space-y-2">
              <Label htmlFor="alert-id">Alert ID (timeline lookup)</Label>
              <Input
                id="alert-id"
                value={alertId}
                onChange={(e) => setAlertId(e.target.value)}
                placeholder="alert_123…"
              />
              <Button
                variant="secondary"
                disabled={!alertId || loadingAction !== null || !canReadTimeline}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("timeline");
                  try {
                    const data = await getAlertTimeline(alertId);
                    setTimelineResult(data);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "timeline"} loading="Loading" idle="Fetch Timeline" />
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="stack-grid">
          {error ? <ErrorCard message={error} /> : null}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Alert Status</CardTitle>
              <CardDescription>Quick summary before diving into raw traces.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Latest Alert ID</div>
                  <div className="mt-1 break-all text-sm font-medium">{triggeredAlertId ?? "Not triggered yet"}</div>
                </div>
                <div className="metric-card">
                  <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Timeline Events</div>
                  <div className="mt-1 text-sm font-medium">{timelineCount ?? "No timeline loaded"}</div>
                </div>
              </div>
            </CardContent>
          </Card>
          <TimelineList
            title="Outbox Timeline Events"
            description="Delivery state changes from the alert timeline endpoint."
            items={outboxTimeline.slice(0, 8).map((item, idx) => ({
              id: String(item.event_id ?? item.id ?? idx),
              title: String(item.status ?? item.event_type ?? "event"),
              subtitle: String(item.timestamp ?? item.created_at ?? item.occurred_at ?? "No timestamp"),
              badges: "destination" in item ? [String(item.destination)] : [],
            }))}
            emptyLabel="Fetch a timeline to view delivery state changes."
          />
          <TimelineList
            title="Trigger Workflow Timeline"
            description="Execution steps from the trigger workflow response."
            items={triggerWorkflowTimeline.slice(0, 6).map((item, idx) => ({
              id: String(item.event_id ?? idx),
              title: String(item.event_name ?? item.node_name ?? item.stage ?? item.event_type ?? "workflow_event"),
              subtitle: String(item.timestamp ?? item.created_at ?? "No timestamp"),
            }))}
            emptyLabel="Trigger an alert to preview workflow execution steps."
          />
          <JsonViewer title="Trigger Response" data={result} emptyLabel="Trigger an alert to inspect outbox and workflow trace data." />
          <JsonViewer title="Timeline Response" data={timelineResult} emptyLabel="Fetch a timeline to inspect delivery state history." />
        </div>
      </div>
    </div>
  );
}
