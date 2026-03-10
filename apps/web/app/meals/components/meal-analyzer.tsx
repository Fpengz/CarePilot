"use client";

import { useRef, useState } from "react";
import { ImagePlus, X } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { AsyncLabel } from "@/components/app/async-label";
import { analyzeMeal } from "@/lib/api/meal-client";
import type { MealAnalyzeApiResponse } from "@/lib/types";

const DEFAULT_MEAL_PROVIDER = process.env.NEXT_PUBLIC_MEAL_ANALYZE_PROVIDER ?? "test";

interface MealAnalyzerProps {
  onSuccess: (data: MealAnalyzeApiResponse) => void;
}

export function MealAnalyzer({ onSuccess }: MealAnalyzerProps) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);

  const mutation = useMutation({
    mutationFn: (formData: FormData) => analyzeMeal(formData),
    onSuccess: (data) => {
      onSuccess(data);
      void queryClient.invalidateQueries({ queryKey: ["meal-daily-summary"] });
      void queryClient.invalidateQueries({ queryKey: ["meal-records"] });
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0] ?? null);
  };

  const handleAnalyze = () => {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    form.append("runtime_mode", "local");
    form.append("provider", DEFAULT_MEAL_PROVIDER);
    mutation.mutate(form);
  };

  const handleClear = () => {
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <Card className="grain-overlay">
      <CardHeader>
        <CardTitle>Analyze Meal</CardTitle>
        <CardDescription>
          Upload an image to identify dishes, estimate nutrition, and log to your history.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <input
            ref={fileInputRef}
            id="meal-file"
            className="sr-only"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleFileChange}
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
                    {file ? `${file.name} • ${(file.size / 1024).toFixed(0)} KB` : "JPG, PNG, or WEBP uploads."}
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                <Button variant="secondary" onClick={() => fileInputRef.current?.click()} className="w-full sm:w-auto">
                  {file ? "Replace Image" : "Browse Files"}
                </Button>
                {file && (
                  <Button variant="ghost" onClick={handleClear} className="gap-1.5 sm:w-auto">
                    <X className="h-4 w-4" aria-hidden /> Clear
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button disabled={!file || mutation.isPending} onClick={handleAnalyze}>
            <AsyncLabel active={mutation.isPending} loading="Analyzing" idle="Analyze Meal" />
          </Button>
        </div>

        <Separator />
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="metric-card">
            <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Analyze Provider</div>
            <div className="mt-1 text-sm font-medium">{DEFAULT_MEAL_PROVIDER}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
