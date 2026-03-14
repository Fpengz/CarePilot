"use client";

import { useState } from "react";
import { PageTitle } from "@/components/app/page-title";
import type { MealAnalyzeApiResponse } from "@/lib/types";

import { MealAnalyzer } from "./components/meal-analyzer";
import { MealRecordsList } from "./components/meal-records-list";
import { NutritionProgress } from "./components/nutrition-progress";

export default function MealsPage() {
  const [lastAnalysis, setLastAnalysis] = useState<MealAnalyzeApiResponse | null>(null);

  return (
    <div className="section-stack">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Nutrition Intelligence</h1>
        <p className="text-[color:var(--muted-foreground)] leading-relaxed max-w-2xl">
          Log meals through vision-based analysis, monitor macronutrient trends, and stay within your clinical glycemic targets.
        </p>
      </div>

      <div className="page-grid items-start">
        <div className="space-y-8">
          <MealAnalyzer onSuccess={setLastAnalysis} />
          <MealRecordsList />
        </div>

        <div className="space-y-8 lg:sticky lg:top-28">
          <NutritionProgress />
        </div>
      </div>
    </div>
  );
}
