"use client";

import { useRef, useState } from "react";
import { ImagePlus, X } from "lucide-react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { JsonViewer } from "@/components/app/json-viewer";
import { PageTitle } from "@/components/app/page-title";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { analyzeMeal, listMealRecords } from "@/lib/api";
import type { MealAnalyzeApiResponse } from "@/lib/types";

const DEFAULT_MEAL_PROVIDER = process.env.NEXT_PUBLIC_MEAL_ANALYZE_PROVIDER ?? "test";

export default function MealsPage() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<MealAnalyzeApiResponse | null>(null);
  const [recordsResult, setRecordsResult] = useState<object | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<"analyze" | "records" | null>(null);
  const recordItems = (recordsResult as { records?: Array<Record<string, unknown>> } | null)?.records ?? [];

  return (
    <div>
      <PageTitle
        eyebrow="Meals"
        title="Meal Analysis and Record Review"
        description="Upload a meal image for analysis and inspect the persisted meal records endpoint introduced in the API refactor."
        tags={["member scope", "workflow trace"]}
      />

      <div className="page-grid">
        <Card className="grain-overlay">
          <CardHeader>
            <CardTitle>Analyze Meal</CardTitle>
            <CardDescription>
              Uploads an image to `/api/v1/meal/analyze`, stores a meal record, and returns a typed summary for UI rendering.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="meal-file" className="text-sm font-medium">
                Meal image
              </label>
              <input
                ref={fileInputRef}
                id="meal-file"
                className="sr-only"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <div className="rounded-2xl border border-dashed border-[color:var(--border)] bg-gradient-to-br from-white/80 to-white/45 p-4 dark:from-[color:var(--panel-soft)] dark:to-[color:var(--panel-soft)]/70">
                <div className="flex flex-col gap-4">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 rounded-xl border border-[color:var(--border)] bg-[color:var(--accent)]/10 p-2.5 text-[color:var(--accent)] dark:bg-[color:var(--accent)]/15">
                      <ImagePlus className="h-4 w-4" aria-hidden />
                    </div>
                    <div className="min-w-0">
                      <div className="text-sm font-semibold">{file ? "Image ready for analysis" : "Upload a meal image"}</div>
                      <div className="app-muted mt-1 text-xs">
                        {file
                          ? `${file.name} • ${(file.size / 1024).toFixed(0)} KB`
                          : "Drop-in style selector for JPG, PNG, and WEBP uploads."}
                      </div>
                    </div>
                  </div>
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                    <Button
                      type="button"
                      size="default"
                      variant="secondary"
                      onClick={() => fileInputRef.current?.click()}
                      className="w-full sm:w-auto"
                    >
                      {file ? "Replace Image" : "Browse Files"}
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      disabled={!file}
                      onClick={() => {
                        setFile(null);
                        if (fileInputRef.current) fileInputRef.current.value = "";
                      }}
                      className="gap-1.5 sm:w-auto"
                    >
                      <X className="h-4 w-4" aria-hidden />
                      Clear
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className="rounded-full border border-[color:var(--border)] bg-white/70 px-2.5 py-1 dark:bg-[color:var(--panel-soft)]">JPG</span>
                    <span className="rounded-full border border-[color:var(--border)] bg-white/70 px-2.5 py-1 dark:bg-[color:var(--panel-soft)]">PNG</span>
                    <span className="rounded-full border border-[color:var(--border)] bg-white/70 px-2.5 py-1 dark:bg-[color:var(--panel-soft)]">WEBP</span>
                  </div>
                </div>
              </div>
              <p className="app-muted text-xs">Accepted formats: JPG, PNG, WEBP.</p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                disabled={!file || loadingAction !== null}
                onClick={async () => {
                  if (!file) return;
                  setError(null);
                  setResult(null);
                  setLoadingAction("analyze");
                  try {
                    const form = new FormData();
                    form.append("file", file);
                    form.append("runtime_mode", "local");
                    form.append("provider", DEFAULT_MEAL_PROVIDER);
                    const data = await analyzeMeal(form);
                    setResult(data);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "analyze"} loading="Analyzing" idle="Analyze Meal" />
              </Button>
              <Button
                variant="secondary"
                disabled={loadingAction !== null}
                onClick={async () => {
                  setError(null);
                  setLoadingAction("records");
                  try {
                    const data = await listMealRecords();
                    setRecordsResult(data);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : String(e));
                  } finally {
                    setLoadingAction(null);
                  }
                }}
              >
                <AsyncLabel active={loadingAction === "records"} loading="Loading" idle="Load Meal Records" />
              </Button>
            </div>

            <Separator />
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="metric-card">
                <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Selected File</div>
                <div className="mt-1 text-sm font-medium">{file?.name ?? "None selected"}</div>
              </div>
              <div className="metric-card">
                <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Read Endpoint</div>
                <div className="mt-1 text-sm font-medium">GET /api/v1/meal/records</div>
              </div>
              <div className="metric-card sm:col-span-2">
                <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Analyze Provider</div>
                <div className="mt-1 text-sm font-medium">{DEFAULT_MEAL_PROVIDER}</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="stack-grid">
          {error ? <ErrorCard message={error} /> : null}
          <Card>
            <CardHeader>
              <CardTitle>Analysis Summary</CardTitle>
              <CardDescription>
                Stable meal summary contract for UI rendering (keeps raw payloads below for debugging).
              </CardDescription>
            </CardHeader>
            <CardContent>
              {result?.summary ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="metric-card">
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Meal</div>
                    <div className="mt-1 text-sm font-medium">{result.summary.meal_name}</div>
                  </div>
                  <div className="metric-card">
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Confidence</div>
                    <div className="mt-1 text-sm font-medium">{Math.round(result.summary.confidence * 100)}%</div>
                  </div>
                  <div className="metric-card">
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Estimated Calories</div>
                    <div className="mt-1 text-sm font-medium">{Math.round(result.summary.estimated_calories)} kcal</div>
                  </div>
                  <div className="metric-card">
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Portion</div>
                    <div className="mt-1 text-sm font-medium">{result.summary.portion_size}</div>
                  </div>
                  <div className="metric-card sm:col-span-2">
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Flags</div>
                    <div className="mt-1 text-sm font-medium">
                      {result.summary.flags.length > 0 ? result.summary.flags.join(", ") : "None"}
                    </div>
                  </div>
                  <div className="metric-card sm:col-span-2">
                    <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Review Status</div>
                    <div className="mt-1 text-sm font-medium">
                      {result.summary.needs_manual_review ? "Manual review recommended" : "Auto-reviewed"}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="app-muted text-sm">Analyze a meal image to view the typed summary.</p>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Saved Meal Records</CardTitle>
              <CardDescription>Recent persisted meals from the read endpoint.</CardDescription>
            </CardHeader>
            <CardContent>
              {recordItems.length > 0 ? (
                <div className="data-list">
                  {recordItems.slice(0, 5).map((record, index) => (
                    <div key={String(record.id ?? record.meal_name ?? index)} className="data-list-row sm:flex-row sm:items-center sm:justify-between">
                      <div className="min-w-0">
                        <div className="text-sm font-medium">{String(record.meal_name ?? "Meal record")}</div>
                        <div className="app-muted mt-1 text-xs">
                          {String(record.captured_at ?? record.created_at ?? "Unknown capture time")}
                        </div>
                      </div>
                      <div className="text-sm font-medium">
                        {typeof record.calories_estimate === "number"
                          ? `${Math.round(record.calories_estimate)} kcal`
                          : typeof record.estimated_calories === "number"
                            ? `${Math.round(Number(record.estimated_calories))} kcal`
                            : "—"}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="app-muted text-sm">Load meal records to preview saved items.</p>
              )}
            </CardContent>
          </Card>
          <JsonViewer title="Analyze Response" description="Workflow trace and persisted meal record payload." data={result} />
          <JsonViewer
            title="Meal Records"
            description="Collection read endpoint for saved meal records."
            data={recordsResult}
            emptyLabel="Load records to inspect persisted meals."
          />
        </div>
      </div>
    </div>
  );
}
