"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { JsonViewer } from "@/components/app/json-viewer";
import { KeyValuePreview } from "@/components/app/key-value-preview";
import { PageTitle } from "@/components/app/page-title";
import { TimelineList } from "@/components/app/timeline-list";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { generateSuggestionFromReport, getSuggestion, listSuggestions } from "@/lib/api";
import type { SuggestionItemApi } from "@/lib/types";
import { useSession } from "@/components/app/session-provider";

const DEFAULT_REPORT = "HbA1c 7.1 LDL 4.2 systolic bp 150 diastolic bp 95";

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export default function SuggestionsPage() {
  const { hasScope, status } = useSession();
  const [reportText, setReportText] = useState(DEFAULT_REPORT);
  const [selected, setSelected] = useState<SuggestionItemApi | null>(null);
  const [items, setItems] = useState<SuggestionItemApi[]>([]);
  const [scope, setScope] = useState<"self" | "household">("self");
  const [sourceFilter, setSourceFilter] = useState<string>("all");
  const [error, setError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<"generate" | "load" | "open" | null>(null);
  const canInspectWorkflow = status === "authenticated" && hasScope("workflow:replay");

  const recommendation = selected?.recommendation;
  const recommendationEntries = useMemo(
    () => Object.entries(recommendation ?? {}).slice(0, 8).map(([key, value]) => ({ key: key.replaceAll("_", " "), value })),
    [recommendation],
  );
  const sourceOptions = useMemo(() => {
    const map = new Map<string, string>();
    for (const item of items) map.set(item.source_user_id, item.source_display_name);
    return Array.from(map.entries()).map(([id, name]) => ({ id, name }));
  }, [items]);
  const visibleItems = useMemo(
    () => items.filter((item) => (sourceFilter === "all" ? true : item.source_user_id === sourceFilter)),
    [items, sourceFilter],
  );

  return (
    <div>
      <PageTitle
        eyebrow="Suggestions"
        title="Report-to-Suggestion Workflow"
        description="Generate structured suggestions from pasted report text with one action, then review persisted suggestion history."
        tags={["unified endpoint", "persisted history"]}
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

            <div className="flex flex-wrap gap-2">
              <Button
                variant={scope === "self" ? "default" : "secondary"}
                disabled={loadingAction !== null}
                onClick={() => setScope("self")}
              >
                Self Scope
              </Button>
              <Button
                variant={scope === "household" ? "default" : "secondary"}
                disabled={loadingAction !== null}
                onClick={() => setScope("household")}
              >
                Household Scope
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant={sourceFilter === "all" ? "default" : "secondary"} onClick={() => setSourceFilter("all")}>
                All Sources
              </Button>
              {sourceOptions.map((source) => (
                <Button
                  key={source.id}
                  variant={sourceFilter === source.id ? "default" : "secondary"}
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
                  try {
                    const response = await generateSuggestionFromReport({ text: reportText });
                    setSelected(response.suggestion);
                    const listResponse = await listSuggestions({ limit: 20, scope });
                    setItems(listResponse.items);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
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
                    const response = await listSuggestions({ limit: 20, scope });
                    setItems(response.items);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "load"} loading="Loading" idle="Load Suggestions" />
              </Button>
            </div>

            {selected ? (
              <div className="metric-card">
                <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Current Suggestion</div>
                <div className="mt-1 text-sm font-medium">{selected.suggestion_id}</div>
                <p className="app-muted mt-2 text-xs">{selected.disclaimer}</p>
                <p className="app-muted mt-2 text-xs">
                  Active history scope: <span className="font-medium">{scope}</span>
                </p>
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
            description="Recent saved suggestions for the current account."
            emptyLabel="No suggestions yet. Generate one from report text."
            items={visibleItems.map((item) => ({
              id: item.suggestion_id,
              title: item.suggestion_id,
              subtitle: `${item.source_display_name} · ${formatDate(item.created_at)}`,
              badges: [item.safety.decision, String(item.recommendation.safe ? "safe" : "review")],
              onClick: async () => {
                setError(null);
                setLoadingAction("open");
                try {
                  const detail = await getSuggestion(item.suggestion_id, { scope });
                  setSelected(detail.suggestion);
                } catch (e) {
                  setError(e instanceof Error ? e.message : String(e));
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
            emptyLabel="Generate or open a suggestion to inspect safety decision fields."
          />

          <KeyValuePreview
            title="Recommendation Preview"
            description="Top fields from the generated recommendation payload."
            entries={recommendationEntries}
            emptyLabel="Generate or open a suggestion to preview recommendation fields."
          />

          <TimelineList
            title="Workflow Timeline"
            description="Request/correlation-linked timeline events for this suggestion run."
            emptyLabel="No workflow events yet."
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

          <JsonViewer
            title="Selected Suggestion"
            data={selected}
            emptyLabel="Generate or load suggestions to inspect the full payload."
          />
        </div>
      </div>
    </div>
  );
}
