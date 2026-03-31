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
    <main className="section-stack relative isolate max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 pb-12 bg-background min-h-screen">
      <div className="dashboard-grounding" aria-hidden="true" />
      <header className="flex flex-col gap-2 py-10">
        <h1 className="text-h1 font-display tracking-tight text-foreground">Nutrition Intelligence</h1>
        <p className="text-muted-foreground leading-relaxed max-w-2xl text-sm font-medium">
          Log meals through vision-based analysis, monitor macronutrient trends, and stay within your clinical glycemic targets.
        </p>
      </header>

      <div className="grid grid-cols-12 gap-12 items-start">
        <div className="col-span-12 lg:col-span-8 space-y-12">
          <section aria-label="Meal Analyzer">
            <MealAnalyzer onSuccess={setLastAnalysis} />
          </section>
          <section aria-label="Meal History">
            <MealRecordsList />
          </section>
        </div>

        <aside className="col-span-12 lg:col-span-4 space-y-10 lg:sticky lg:top-28">
          <NutritionProgress />
        </aside>
      </div>
    </main>
  );
}
