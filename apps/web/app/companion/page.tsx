"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getCompanionToday } from "@/lib/api/companion-client";
import type { CompanionInteractionApiResponse } from "@/lib/types";

import { CarePlanCard } from "./components/care-plan-card";
import { ClinicianDigestCard } from "./components/clinician-digest-card";
import { ImpactWatchCard } from "./components/impact-watch-card";
import { InteractionForm } from "./components/interaction-form";
import { SupportingEvidenceCard } from "./components/supporting-evidence-card";

export default function CompanionPage() {
  const queryClient = useQueryClient();
  const [interaction, setInteraction] = useState<CompanionInteractionApiResponse | null>(null);

  const {
    data: today,
    error,
    isFetching,
  } = useQuery({
    queryKey: ["companion-today"],
    queryFn: getCompanionToday,
  });

  const active = interaction ?? today;

  const handleRefreshToday = () => {
    void queryClient.invalidateQueries({ queryKey: ["companion-today"] });
    setInteraction(null);
  };

  return (
    <div>
      <PageTitle
        eyebrow="Companion"
        title="AI Health Companion"
        description="Turn your health signals into a personalized next-best action, clinical rationale, and impact insight."
      />

      <div className="page-grid">
        <div className="space-y-6">
          <InteractionForm
            todayData={today}
            isRefreshing={isFetching}
            onRefresh={handleRefreshToday}
            onSuccess={setInteraction}
          />
          {error ? <ErrorCard message={error instanceof Error ? error.message : String(error)} /> : null}
        </div>

        <Tabs defaultValue="plan" className="w-full">
          <TabsList className="mb-4 grid w-full grid-cols-3 lg:w-auto lg:inline-flex">
            <TabsTrigger value="plan">Active Plan</TabsTrigger>
            <TabsTrigger value="evidence">Evidence</TabsTrigger>
            <TabsTrigger value="clinical">Clinical / Impact</TabsTrigger>
          </TabsList>

          <TabsContent value="plan" className="space-y-6 mt-0">
            <CarePlanCard carePlan={active?.care_plan} />
          </TabsContent>

          <TabsContent value="evidence" className="space-y-6 mt-0">
            <SupportingEvidenceCard citations={active?.care_plan.citations ?? []} />
          </TabsContent>

          <TabsContent value="clinical" className="space-y-6 mt-0">
            <ClinicianDigestCard digest={active?.clinician_digest_preview} />
            <ImpactWatchCard impact={active?.impact} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
