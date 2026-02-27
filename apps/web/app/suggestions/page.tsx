"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { KeyValuePreview } from "@/components/app/key-value-preview";
import { PageTitle } from "@/components/app/page-title";
import { TimelineList } from "@/components/app/timeline-list";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useSession } from "@/components/app/session-provider";
import { generateSuggestionFromReport, getSuggestion, listSuggestions } from "@/lib/api";
import {
  buildSuggestionDetail,
  buildSuggestionSummaries,
  toSuggestionErrorMessage,
  type SuggestionsLoadState,
  type SuggestionScope,
} from "@/lib/suggestions-view-model";
import type { SuggestionItemApi } from "@/lib/types";

const DEFAULT_REPORT = "HbA1c 7.1 LDL 4.2 systolic bp 150 diastolic bp 95";

export default function SuggestionsPage() {
  const { hasScope, status } = useSession();
  const [reportText, setReportText] = useState(DEFAULT_REPORT);
  const [selected, setSelected] = useState<SuggestionItemApi | null>(null);
  const [items, setItems] = useState<SuggestionItemApi[]>([]);
  const [scope, setScope] = useState<SuggestionScope>("self");
  const [sourceFilter, setSourceFilter] = useState<string>("all");
  const [listState, setListState] = useState<SuggestionsLoadState>("idle");
  const [detailState, setDetailState] = useState<SuggestionsLoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<"generate" | "load" | "open" | null>(null);
  const canInspectWorkflow = status === "authenticated" && hasScope("workflow:replay");

  const summaries = useMemo(() => buildSuggestionSummaries(items), [items]);
  const detail = useMemo(() => buildSuggestionDetail(selected), [selected]);

  const sourceOptions = useMemo(() => {
    const map = new Map<string, string>();
    for (const item of items) map.set(item.source_user_id, item.source_display_name);
    return Array.from(map.entries()).map(([id, name]) => ({ id, name }));
  }, [items]);

  const visibleItems = useMemo(
    () => summaries.filter((item) => (sourceFilter === "all" ? true : item.sourceUserId === sourceFilter)),
    [summaries, sourceFilter],
  );

  const sourceUserIdParam = sourceFilter === "all" ? undefined : sourceFilter;

  async function refreshSuggestions() {
    setListState("loading");
    const response = await listSuggestions({
      limit: 20,
      scope,
      sourceUserId: sourceUserIdParam,
    });
    setItems(response.items);
    setListState("ready");
  }

  return (
    <div>
      <PageTitle
        eyebrow="Suggestions"
        title="Report-to-Suggestion Workflow"
        description="Generate structured suggestions from pasted report text and review saved history with scope-aware filters."
        tags={["workflow visibility", "typed states"]}
      />

      <div className="page-grid">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Generate Suggestion</CardTitle>
            <CardDescription>
              Uses `POST /api/v1/suggestions/generate-from-report` and stores a reusable suggestion snapshot.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="suggestions-report-text">Report text</Label>
              <Textarea
                id="suggestions-report-text"
                className="app-code min-h-[180px] bg-[#161714] text-[#ece8dc] placeholder:text-[#b3b7ae]"
                rows={7}
                value={reportText}
                onChange={(e) => setReportText(e.target.value)}
              />
            </div>

            <div className="flex flex-wrap gap-2" role="group" aria-label="Suggestion visibility scope">
              <Button
                variant={scope === "self" ? "default" : "secondary"}
                disabled={loadingAction !== null}
                aria-pressed={scope === "self"}
                onClick={() => setScope("self")}
              >
                Self Scope
              </Button>
              <Button
                variant={scope === "household" ? "default" : "secondary"}
                disabled={loadingAction !== null}
                aria-pressed={scope === "household"}
                onClick={() => setScope("household")}
              >
                Household Scope
              </Button>
            </div>

            <div className="flex flex-wrap gap-2" role="group" aria-label="Filter suggestions by source user">
              <Button
                variant={sourceFilter === "all" ? "default" : "secondary"}
                disabled={listState === "loading"}
                aria-pressed={sourceFilter === "all"}
                onClick={() => setSourceFilter("all")}
              >
                All Sources
              </Button>
              {sourceOptions.map((source) => (
                <Button
                  key={source.id}
                  variant={sourceFilter === source.id ? "default" : "secondary"}
                  disabled={listState === "loading"}
                  aria-pressed={sourceFilter === source.id}
                  onClick={() => setSourceFilter(source.id)}
                >
                  {source.name}
                </Button>
              ))}
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                disabled={loadingAction !== null || reportText.trim().length === 0}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("generate");
                  setDetailState("loading");
                  try {
                    const response = await generateSuggestionFromReport({ text: reportText });
                    setSelected(response.suggestion);
                    setDetailState("ready");
                    await refreshSuggestions();
                  } catch (e) {
                    setError(toSuggestionErrorMessage(e));
                    setDetailState("error");
                    setListState("error");
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "generate"} loading="Generating" idle="Generate Suggestion" />
              </Button>

              <Button
                variant="secondary"
                disabled={loadingAction !== null}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("load");
                  try {
                    await refreshSuggestions();
                  } catch (e) {
                    setError(toSuggestionErrorMessage(e));
                    setListState("error");
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "load"} loading="Loading" idle="Load Suggestions" />
              </Button>
            </div>

            <div aria-live="polite" className="app-muted text-xs">
              {listState === "loading" ? "Refreshing suggestions list..." : `Showing ${visibleItems.length} suggestion(s).`}
            </div>

            {selected ? (
              <div className="metric-card">
                <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Current Suggestion</div>
                <div className="mt-1 text-sm font-medium">{selected.suggestion_id}</div>
                <p className="app-muted mt-2 text-xs">{selected.disclaimer}</p>
                <p className="app-muted mt-2 text-xs">
                  Active history scope: <span className="font-medium">{scope}</span>
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {detail?.isPartial ? <Badge variant="outline">Partial Data</Badge> : <Badge>Complete</Badge>}
                  <Badge variant="outline">{selected.safety.decision}</Badge>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button variant="secondary" size="sm" className="h-8 px-2 text-xs" asChild>
                    <Link href={`/workflows?correlation_id=${selected.workflow.correlation_id}`}>
                      Open Workflow Trace
                    </Link>
                  </Button>
                  {!canInspectWorkflow ? (
                    <span className="app-muted text-xs">
                      Admin scope `workflow:replay` required to load trace details.
                    </span>
                  ) : null}
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <div className="stack-grid">
          {error ? <ErrorCard message={error} /> : null}

          <TimelineList
            title="Suggestion History"
            description="Recent saved suggestions for the current account and selected scope."
            emptyLabel={listState === "loading" ? "Loading suggestions..." : "No suggestions yet for this scope/filter."}
            items={visibleItems.map((item) => ({
              id: item.id,
              title: item.id,
              subtitle: `${item.sourceDisplayName} · ${item.createdAtLabel}`,
              badges: [item.safetyDecision, item.safe ? "safe" : "review"],
              onClick: async () => {
                setError(null);
                setLoadingAction("open");
                setDetailState("loading");
                try {
                  const detailResponse = await getSuggestion(item.id, { scope });
                  setSelected(detailResponse.suggestion);
                  setDetailState("ready");
                } catch (e) {
                  setError(toSuggestionErrorMessage(e));
                  setDetailState("error");
                } finally {
                  setLoadingAction(null);
                }
              },
            }))}
          />

          <KeyValuePreview
            title="Safety Decision"
            description="Structured safety gate output for this suggestion."
            entries={
              selected
                ? [
                    { key: "decision", value: selected.safety.decision },
                    { key: "reasons", value: selected.safety.reasons.join(", ") || "none" },
                    { key: "required actions", value: selected.safety.required_actions.join(" | ") || "none" },
                  ]
                : []
            }
            emptyLabel={detailState === "loading" ? "Loading safety details..." : "Open a suggestion to inspect safety details."}
          />

          <KeyValuePreview
            title="Detail Integrity"
            description="Detects partial payloads and missing fields before clinical review."
            entries={
              detail
                ? [
                    { key: "status", value: detail.isPartial ? "partial" : "complete" },
                    { key: "parsed readings", value: detail.hasReadings ? "available" : "missing" },
                    { key: "workflow events", value: detail.hasWorkflowEvents ? "available" : "missing" },
                    { key: "recommendation advice", value: detail.hasRecommendationAdvice ? "available" : "missing" },
                    { key: "risk flags", value: detail.hasRiskFlags ? "present" : "none" },
                  ]
                : []
            }
            emptyLabel={detailState === "loading" ? "Loading suggestion detail..." : "Open a suggestion to validate detail completeness."}
          />

          {detail?.isPartial ? (
            <Card>
              <CardHeader>
                <CardTitle>Partial Data Warnings</CardTitle>
                <CardDescription>Some suggestion fields are missing and may require regeneration.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {detail.partialReasons.map((reason) => (
                  <p key={reason} className="app-muted text-sm">
                    {reason}
                  </p>
                ))}
              </CardContent>
            </Card>
          ) : null}

          <TimelineList
            title="Workflow Timeline"
            description="Request/correlation-linked timeline events for this suggestion run."
            emptyLabel={detailState === "loading" ? "Loading workflow events..." : "No workflow events available."}
            items={(selected?.workflow.timeline_events ?? []).map((event, index) => {
              const obj = event as Record<string, unknown>;
              return {
                id: `${String(obj.event_type ?? "event")}-${index}`,
                title: String(obj.event_type ?? "event"),
                subtitle: String(obj.created_at ?? ""),
                badges: [String(obj.request_id ?? ""), String(obj.correlation_id ?? "")].filter(Boolean),
              };
            })}
          />

          {selected ? (
            <details>
              <summary className="cursor-pointer text-sm font-medium">Raw payload (debug)</summary>
              <pre className="app-code mt-2 overflow-auto rounded-md p-3 text-xs">{JSON.stringify(selected, null, 2)}</pre>
            </details>
          ) : null}
        </div>
      </div>
    </div>
  );
}
