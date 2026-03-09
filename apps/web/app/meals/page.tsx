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

  return (
    <div>
      <PageTitle
        eyebrow="Meals"
        title="Meal Analysis and Record Review"
        description="Log meals, inspect saved records, and track how much room is left in today’s nutrition targets."
        tags={["daily tracking", "member scope", "workflow trace"]}
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
            <TabsTrigger value="debug">Analysis Debug</TabsTrigger>
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

          <TabsContent value="debug" className="space-y-6 mt-0">
            <Card>
              <CardHeader>
                <CardTitle>Analysis Summary</CardTitle>
                <CardDescription>
                  Detailed breakdown of the last analyzed meal.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {lastAnalysis?.summary ? (
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Meal</div>
                      <div className="mt-1 text-sm font-medium">{lastAnalysis.summary.meal_name}</div>
                    </div>
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Confidence</div>
                      <div className="mt-1 text-sm font-medium">{Math.round(lastAnalysis.summary.confidence * 100)}%</div>
                    </div>
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Calories</div>
                      <div className="mt-1 text-sm font-medium">{Math.round(lastAnalysis.summary.estimated_calories)} kcal</div>
                    </div>
                    <div className="metric-card">
                      <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Portion</div>
                      <div className="mt-1 text-sm font-medium">{lastAnalysis.summary.portion_size}</div>
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
