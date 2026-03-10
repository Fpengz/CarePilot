"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { KeyValuePreview } from "@/components/app/key-value-preview";
import { TimelineList } from "@/components/app/timeline-list";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useSession } from "@/components/app/session-provider";
import { generateSuggestionFromReport, getSuggestion, listSuggestions } from "@/lib/api/recommendation-client";
import {
  buildSuggestionDetail,
  buildSuggestionSummaries,
  toSuggestionErrorMessage,
  type SuggestionsLoadState,
  type SuggestionScope,
} from "@/lib/suggestions-view-model";
import type { SuggestionItemApi } from "@/lib/types";

const DEFAULT_REPORT = "HbA1c 7.1 LDL 4.2 systolic bp 150 diastolic bp 95";

export function ClinicalSuggestionsTab() {
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
    <div className="space-y-6">
      <div className="page-grid">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Generate Suggestion</CardTitle>
            <CardDescription>
              Generate structured suggestions from pasted report text using AI analysis.
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
                <AsyncLabel active={loadingAction === "load"} loading="Loading" idle="Load History" />
              </Button>
            </div>

            {selected ? (
              <div className="metric-card">
                <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Current Suggestion</div>
                <div className="mt-1 text-sm font-medium">{selected.suggestion_id}</div>
                <p className="app-muted mt-2 text-xs">{selected.disclaimer}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button variant="secondary" size="sm" className="h-8 px-2 text-xs" asChild>
                    <Link href={`/workflows?correlation_id=${selected.workflow.correlation_id}`}>
                      Open Workflow Trace
                    </Link>
                  </Button>
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
        </div>
      </div>
    </div>
  );
}
