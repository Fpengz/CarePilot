"use client";

import { useState } from "react";
import { PageTitle } from "@/components/app/page-title";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { JsonViewer } from "@/components/app/json-viewer";
import type { MealAnalyzeApiResponse } from "@/lib/types";

import { MealAnalyzer } from "./components/meal-analyzer";
import { MealRecordsList } from "./components/meal-records-list";
import { NutritionProgress } from "./components/nutrition-progress";
import { WeeklyPattern } from "./components/weekly-pattern";
import { DailyMealSuggestions } from "./components/daily-meal-suggestions";

export default function MealsPage() {
  const [lastAnalysis, setLastAnalysis] = useState<MealAnalyzeApiResponse | null>(null);
  const validated = lastAnalysis?.validated_event as Record<string, unknown> | undefined;
  const nutrition = lastAnalysis?.nutrition_profile as Record<string, unknown> | undefined;
  const observation = lastAnalysis?.raw_observation as Record<string, unknown> | undefined;

  const mealName = typeof validated?.meal_name === "string" ? validated.meal_name : "Meal";
  const capturedAtRaw = typeof validated?.captured_at === "string" ? validated.captured_at : "";
  const capturedAt =
    capturedAtRaw && !Number.isNaN(Date.parse(capturedAtRaw)) ? new Date(capturedAtRaw).toLocaleString() : "—";
  const caloriesText = typeof nutrition?.calories === "number" ? `${Math.round(nutrition.calories)} kcal` : "—";
  const confidenceText =
    typeof observation?.confidence_score === "number" ? `${Math.round(observation.confidence_score * 100)}%` : "—";

  return (
    <div>
      <PageTitle
        eyebrow="Meals"
        title="Meal Analysis and Nutrition Review"
        description="Log meals, inspect saved records, and track how much room is left in today’s nutrition targets."
        tags={["daily tracking"]}
      />

      <div className="page-grid">
        <div className="space-y-6">
          <MealAnalyzer onSuccess={setLastAnalysis} />
          <NutritionProgress />
        </div>

        <Tabs defaultValue="history" className="w-full">
          <TabsList className="mb-4 grid w-full grid-cols-4 lg:w-auto lg:inline-flex">
            <TabsTrigger value="history">History</TabsTrigger>
            <TabsTrigger value="suggestions">Suggestions</TabsTrigger>
            <TabsTrigger value="weekly">Weekly</TabsTrigger>
            <TabsTrigger value="analysis">Latest</TabsTrigger>
          </TabsList>

          <TabsContent value="history" className="space-y-6 mt-0">
            <MealRecordsList />
          </TabsContent>

          <TabsContent value="suggestions" className="space-y-6 mt-0">
            <DailyMealSuggestions />
          </TabsContent>

          <TabsContent value="weekly" className="space-y-6 mt-0">
            <WeeklyPattern />
          </TabsContent>

          <TabsContent value="analysis" className="space-y-6 mt-0">
            <Card>
              <CardHeader>
                <CardTitle>Latest Analysis</CardTitle>
                <CardDescription>Nutritional breakdown of the most recently analyzed meal image.</CardDescription>
              </CardHeader>
              <CardContent>
                {lastAnalysis ? (
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Meal</div>
                      <div className="mt-1 text-sm font-medium">{mealName}</div>
                    </div>
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Confidence</div>
                      <div className="mt-1 text-sm font-medium">{confidenceText}</div>
                    </div>
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Calories</div>
                      <div className="mt-1 text-sm font-medium">{caloriesText}</div>
                    </div>
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Portion</div>
                      <div className="mt-1 text-sm font-medium">—</div>
                    </div>
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Captured</div>
                      <div className="mt-1 text-sm font-medium">{capturedAt}</div>
                    </div>
                  </div>
                ) : (
                  <p className="app-muted text-sm">Analyze a meal image to view details.</p>
                )}
              </CardContent>
            </Card>
            <JsonViewer title="Raw Response" description="Workflow trace payload." data={lastAnalysis} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
