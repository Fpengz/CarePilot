"use client";

import { useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { JsonViewer } from "@/components/app/json-viewer";
import { PageTitle } from "@/components/app/page-title";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getAlertTimeline, triggerAlert } from "@/lib/api";

export default function AlertsPage() {
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
            <Button
              disabled={loadingAction !== null}
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
                disabled={!alertId || loadingAction !== null}
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
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Outbox Timeline Events</CardTitle>
              <CardDescription>Delivery state changes from the alert timeline endpoint.</CardDescription>
            </CardHeader>
            <CardContent>
              {outboxTimeline.length > 0 ? (
                <div className="data-list">
                  {outboxTimeline.slice(0, 8).map((item, idx) => (
                    <div key={String(item.event_id ?? item.id ?? idx)} className="data-list-row">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-medium">{String(item.status ?? item.event_type ?? "event")}</span>
                        {"destination" in item ? (
                          <span className="rounded-full border border-[color:var(--border)] px-2 py-1 text-xs">
                            {String(item.destination)}
                          </span>
                        ) : null}
                      </div>
                      <div className="app-muted text-xs">
                        {String(item.timestamp ?? item.created_at ?? item.occurred_at ?? "No timestamp")}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="app-muted text-sm">Fetch a timeline to view delivery state changes.</p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Trigger Workflow Timeline</CardTitle>
              <CardDescription>Execution steps from the trigger workflow response.</CardDescription>
            </CardHeader>
            <CardContent>
              {triggerWorkflowTimeline.length > 0 ? (
                <div className="data-list">
                  {triggerWorkflowTimeline.slice(0, 6).map((item, idx) => (
                    <div key={String(item.event_id ?? idx)} className="data-list-row">
                      <div className="text-sm font-medium">
                        {String(item.event_name ?? item.node_name ?? item.stage ?? item.event_type ?? "workflow_event")}
                      </div>
                      <div className="app-muted text-xs">
                        {String(item.timestamp ?? item.created_at ?? "No timestamp")}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="app-muted text-sm">Trigger an alert to preview workflow execution steps.</p>
              )}
            </CardContent>
          </Card>
          <JsonViewer title="Trigger Response" data={result} emptyLabel="Trigger an alert to inspect outbox and workflow trace data." />
          <JsonViewer title="Timeline Response" data={timelineResult} emptyLabel="Fetch a timeline to inspect delivery state history." />
        </div>
      </div>
    </div>
  );
}
