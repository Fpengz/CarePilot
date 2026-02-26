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
          <JsonViewer title="Trigger Response" data={result} emptyLabel="Trigger an alert to inspect outbox and workflow trace data." />
          <JsonViewer title="Timeline Response" data={timelineResult} emptyLabel="Fetch a timeline to inspect delivery state history." />
        </div>
      </div>
    </div>
  );
}
