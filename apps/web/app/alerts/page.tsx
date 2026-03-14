"use client";

import { useState } from "react";
import { ShieldAlert, History, Terminal, PlayCircle, RefreshCcw } from "lucide-react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { JsonViewer } from "@/components/app/json-viewer";
import { TimelineList } from "@/components/app/timeline-list";
import { useSession } from "@/components/app/session-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getAlertTimeline, triggerAlert } from "@/lib/api/workflow-client";
import { cn } from "@/lib/utils";

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
    <div className="section-stack">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 text-rose-600">
          <ShieldAlert className="h-5 w-5" />
          <span className="text-[10px] font-bold uppercase tracking-[0.2em]">Privileged Operations</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight">System Integrity & Alerts</h1>
        <p className="text-[color:var(--muted-foreground)] leading-relaxed max-w-2xl text-sm">
          Trigger system-wide care alerts and inspect delivery outbox history for administrative auditing.
        </p>
      </div>

      {!canTrigger || !canReadTimeline ? (
        <div className="rounded-xl border border-dashed border-rose-200 bg-rose-50/50 p-4 text-sm text-rose-800">
          <p className="font-bold flex items-center gap-2 mb-1">
            <Terminal className="h-4 w-4" /> Insufficient Privileges
          </p>
          <p className="opacity-80">Admin scopes required: {!canTrigger ? "[alert:trigger] " : ""}{!canReadTimeline ? "[alert:timeline:read]" : ""}</p>
        </div>
      ) : null}

      <div className="page-grid items-start">
        <div className="space-y-8">
          <div className="clinical-card space-y-8">
            <div className="space-y-1">
              <h3 className="clinical-subtitle">Alert Dispatch</h3>
              <p className="clinical-body">Manually trigger an asynchronous alert workflow.</p>
            </div>

            <div className="space-y-6">
              <Button
                className="w-full h-12 rounded-xl font-bold shadow-sm"
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
                <div className="flex items-center gap-2">
                  <PlayCircle className="h-4 w-4" />
                  <AsyncLabel active={loadingAction === "trigger"} loading="Dispatching" idle="Trigger Verification Alert" />
                </div>
              </Button>

              <div className="clinical-divider" />

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="alert-id" className="text-[10px] font-bold uppercase tracking-widest opacity-70">Alert ID Trace</Label>
                  <Input
                    id="alert-id"
                    value={alertId}
                    onChange={(e) => setAlertId(e.target.value)}
                    placeholder="alert_..."
                    className="h-11 rounded-xl"
                  />
                </div>
                <Button
                  variant="outline"
                  className="w-full h-11 rounded-xl font-bold"
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
                  <div className="flex items-center gap-2">
                    <RefreshCcw className="h-4 w-4" />
                    <AsyncLabel active={loadingAction === "timeline"} loading="Fetching" idle="Inspect Delivery Timeline" />
                  </div>
                </Button>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Terminal className="h-4 w-4 text-[color:var(--muted-foreground)]" />
              <h4 className="text-xs font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Technical Payload</h4>
            </div>
            <div className="space-y-4">
              <JsonViewer title="Workflow Trace" data={result} emptyLabel="No execution trace captured." />
              <JsonViewer title="Outbox History" data={timelineResult} emptyLabel="No delivery history loaded." />
            </div>
          </div>
        </div>

        <div className="space-y-8 lg:sticky lg:top-28">
          <div className="clinical-card bg-[color:var(--accent)]/5 border-[color:var(--accent)]/10">
            <div className="flex items-center gap-2 text-[color:var(--accent)] mb-4">
              <Terminal className="h-4 w-4" />
              <span className="text-[10px] font-bold uppercase tracking-widest">Operation Status</span>
            </div>
            <div className="grid gap-4">
              <div className="space-y-1">
                <div className="text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)] opacity-70">Latest Correlation</div>
                <div className="text-xs font-mono font-medium truncate">{triggeredAlertId ?? "None"}</div>
              </div>
              <div className="space-y-1">
                <div className="text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)] opacity-70">Timeline Events</div>
                <div className="text-xl font-bold">{timelineCount ?? 0}</div>
              </div>
            </div>
          </div>

          <TimelineList
            title="Execution Steps"
            description="Trigger workflow lifecycle"
            items={triggerWorkflowTimeline.slice(0, 6).map((item, idx) => ({
              id: String(item.event_id ?? idx),
              title: String(item.event_name ?? item.node_name ?? "Step"),
              subtitle: String(item.timestamp ?? item.created_at ?? "Pending"),
            }))}
            emptyLabel="Waiting for dispatch..."
          />

          <TimelineList
            title="Outbox State"
            description="Delivery channel updates"
            items={outboxTimeline.slice(0, 8).map((item, idx) => ({
              id: String(item.event_id ?? item.id ?? idx),
              title: String(item.status ?? "Update"),
              subtitle: String(item.timestamp ?? "No date"),
              badges: "destination" in item ? [String(item.destination)] : [],
            }))}
            emptyLabel="Waiting for trace..."
          />
        </div>
      </div>
    </div>
  );
}
