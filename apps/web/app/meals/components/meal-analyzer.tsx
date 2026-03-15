"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ImagePlus, X, UploadCloud, RotateCcw } from "lucide-react";
import Image from "next/image";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { AsyncLabel } from "@/components/app/async-label";
import { analyzeMeal } from "@/lib/api/meal-client";
import type { MealAnalyzeApiResponse } from "@/lib/types";
import { MealAnalysisResult } from "./meal-analysis-result";
import { cn } from "@/lib/utils";

const DEFAULT_MEAL_PROVIDER = process.env.NEXT_PUBLIC_MEAL_ANALYZE_PROVIDER ?? "test";

interface MealAnalyzerProps {
  onSuccess: (data: MealAnalyzeApiResponse) => void;
}

export function MealAnalyzer({ onSuccess }: MealAnalyzerProps) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<MealAnalyzeApiResponse | null>(null);
  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const mutation = useMutation({
    mutationFn: (formData: FormData) => analyzeMeal(formData),
    onSuccess: (data) => {
      setResult(data);
      onSuccess(data);
      void queryClient.invalidateQueries({ queryKey: ["meal-daily-summary"] });
      void queryClient.invalidateQueries({ queryKey: ["meal-records"] });
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0] ?? null);
    setResult(null);
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
    setResult(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const isBusy = mutation.isPending;

  return (
    <div className="clinical-card space-y-8">
      <div className="space-y-1">
        <h3 className="clinical-subtitle">Meal Vision</h3>
        <p className="clinical-body">
          Log a meal by uploading an image. Our clinical model will identify ingredients and estimate nutritional load.
        </p>
      </div>

      <div className="space-y-6">
        <input
          ref={fileInputRef}
          id="meal-file"
          className="sr-only"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={handleFileChange}
        />
        
        {!file && (
          <div 
            className="group flex cursor-pointer flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed border-[color:var(--border-soft)] bg-[color:var(--surface)] p-12 transition-all hover:border-[color:var(--accent)] hover:bg-[color:var(--accent)]/[0.02]"
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="rounded-full bg-[color:var(--accent)]/5 p-4 text-[color:var(--accent)] transition-transform group-hover:scale-110">
              <UploadCloud className="h-8 w-8" aria-hidden />
            </div>
            <div className="text-center">
              <div className="text-sm font-bold tracking-tight">Upload Meal Image</div>
              <p className="mt-1 text-xs text-[color:var(--muted-foreground)] opacity-60">
                Drag and drop or click to browse (JPG, PNG, WEBP)
              </p>
            </div>
          </div>
        )}

        {file && (
          <div className="space-y-4">
            <div className="relative aspect-video overflow-hidden rounded-xl border border-[color:var(--border-soft)] shadow-sm">
              <Image 
                src={previewUrl!} 
                alt="Selected meal preview" 
                fill 
                className={cn("object-cover transition-all", isBusy && "scale-105 blur-[2px]")} 
                unoptimized 
              />
              <div className="absolute top-3 right-3 flex gap-2">
                <Button 
                  size="sm" 
                  variant="secondary" 
                  className="h-8 w-8 rounded-full p-0 bg-white/90 backdrop-blur-sm text-black hover:bg-white shadow-sm"
                  onClick={handleClear}
                  aria-label="Remove image"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
              {isBusy && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/10 backdrop-blur-[1px]">
                  <div className="flex flex-col items-center gap-2">
                    <div className="h-8 w-8 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    <span className="text-[10px] font-bold uppercase tracking-widest text-white shadow-sm">Analyzing...</span>
                  </div>
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <Button 
                className="flex-1 rounded-xl h-12 font-bold" 
                disabled={!!isBusy || !!result} 
                onClick={handleAnalyze}
              >
                <AsyncLabel active={!!isBusy} loading="Analyzing" idle="Start Analysis" />
              </Button>
              {result && (
                <Button 
                  variant="secondary" 
                  className="rounded-xl h-12 gap-2" 
                  onClick={handleClear}
                >
                  <RotateCcw className="h-4 w-4" /> New Analysis
                </Button>
              )}
            </div>
          </div>
        )}

        {result && <MealAnalysisResult data={result} />}
      </div>
    </div>
  );
}
