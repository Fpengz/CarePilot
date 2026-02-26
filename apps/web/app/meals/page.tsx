"use client";

import { useState } from "react";

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

export default function MealsPage() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<MealAnalyzeApiResponse | null>(null);
  const [recordsResult, setRecordsResult] = useState<object | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<"analyze" | "records" | null>(null);

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
            <CardDescription>Uploads an image to `/api/v1/meal/analyze` and stores a meal record.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="meal-file" className="text-sm font-medium">
                Meal image
              </label>
              <Input
                id="meal-file"
                className="cursor-pointer file:mr-3 file:rounded-lg file:border-0 file:bg-[color:var(--accent)] file:px-3 file:py-2 file:text-sm file:font-medium file:text-[color:var(--accent-foreground)]"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
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
                    form.append("provider", "test");
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
