"use client";

import { Activity, Thermometer, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { MealAnalyzeApiResponse } from "@/lib/types";

interface MealAnalysisResultProps {
  data: MealAnalyzeApiResponse;
  onConfirm?: () => void;
  onSkip?: () => void;
  confirmationPending?: boolean;
  confirmationStatus?: "confirmed" | "skipped" | null;
}

export function MealAnalysisResult({
  data,
  onConfirm,
  onSkip,
  confirmationPending,
  confirmationStatus,
}: MealAnalysisResultProps) {
  const validated = data.validated_event as any;
  const candidate = data.candidate_event as any;
  const nutrition = data.nutrition_profile as any;
  const observation = data.raw_observation as any;

  const mealName = validated?.meal_name || candidate?.meal_name || "Meal";
  const calories = Math.round(nutrition?.calories || candidate?.total_nutrition?.calories || 0);
  const confidence = Math.round((observation?.confidence_score || 0) * 100);
  const showConfirmation = data.confirmation_required && !confirmationStatus;

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="clinical-divider" />
      
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="clinical-subtitle">Analysis Result</h4>
          <span className="clinical-chip">{confidence}% confidence</span>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-4 space-y-2">
            <div className="flex items-center gap-2 text-[color:var(--accent)]">
              <Activity className="h-3.5 w-3.5" />
              <span className="text-[10px] font-bold uppercase tracking-wider opacity-70">Identification</span>
            </div>
            <div className="text-sm font-semibold truncate">{mealName}</div>
          </div>

          <div className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-4 space-y-2">
            <div className="flex items-center gap-2 text-orange-500">
              <Zap className="h-3.5 w-3.5" />
              <span className="text-[10px] font-bold uppercase tracking-wider opacity-70">Energy</span>
            </div>
            <div className="text-sm font-semibold">{calories} kcal</div>
          </div>

          <div className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-4 space-y-2">
            <div className="flex items-center gap-2 text-blue-500">
              <Thermometer className="h-3.5 w-3.5" />
              <span className="text-[10px] font-bold uppercase tracking-wider opacity-70">Glycemic Risk</span>
            </div>
            <div className="text-sm font-semibold capitalize">{observation?.glycemic_risk_level || "Low"}</div>
          </div>
        </div>

        <div className="rounded-xl bg-[color:var(--accent)]/5 p-4 border border-[color:var(--accent)]/10">
          <p className="text-xs leading-relaxed text-[color:var(--muted-foreground)]">
            <span className="font-bold text-[color:var(--accent)] uppercase tracking-tighter mr-2">Companion Insight:</span>
            {observation?.summary_narrative || "Analysis complete. This meal has been logged to your daily record."}
          </p>
        </div>

        {showConfirmation && (
          <div className="flex flex-wrap items-center gap-3 rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-4">
            <div className="text-sm">
              <div className="font-semibold">Confirm this meal?</div>
              <div className="text-xs text-[color:var(--muted-foreground)]">
                We need a quick confirmation before logging.
              </div>
            </div>
            <div className="ml-auto flex gap-2">
              <Button
                size="sm"
                className="rounded-full px-4"
                onClick={onConfirm}
                disabled={!!confirmationPending}
              >
                Confirm
              </Button>
              <Button
                size="sm"
                variant="secondary"
                className="rounded-full px-4"
                onClick={onSkip}
                disabled={!!confirmationPending}
              >
                Skip
              </Button>
            </div>
          </div>
        )}

        {confirmationStatus && (
          <div className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] px-4 py-3 text-xs text-[color:var(--muted-foreground)]">
            {confirmationStatus === "confirmed"
              ? "Meal confirmed and logged."
              : "Meal skipped. No entry was logged."}
          </div>
        )}
      </div>
    </div>
  );
}
