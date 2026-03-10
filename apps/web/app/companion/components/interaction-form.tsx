"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { AsyncLabel } from "@/components/app/async-label";
import { runCompanionInteraction } from "@/lib/api/companion-client";
import type { CompanionInteractionApiResponse, CompanionTodayApiResponse } from "@/lib/types";

const INTERACTION_PRESETS: Record<
  "chat" | "meal_review" | "check_in" | "report_follow_up" | "adherence_follow_up",
  { label: string; message: string; emotionText: string }
> = {
  chat: {
    label: "Chat",
    message: "Explain why my current pattern matters and what I should focus on first.",
    emotionText: "I want a clearer explanation without being overwhelmed.",
  },
  meal_review: {
    label: "Meal Review",
    message: "I had another oily hawker lunch. Give me one realistic food swap for the next meal.",
    emotionText: "I feel discouraged about repeating the same lunch choices.",
  },
  check_in: {
    label: "Check-In",
    message: "Help me decide on one realistic next step for today.",
    emotionText: "I feel a bit discouraged about staying consistent.",
  },
  report_follow_up: {
    label: "Report Follow-Up",
    message: "My report looks worrying. What is the main thing I should follow up on now?",
    emotionText: "I am anxious about what the latest results mean.",
  },
  adherence_follow_up: {
    label: "Adherence Follow-Up",
    message: "I missed my meds again because I was rushing. Help me protect the next dose.",
    emotionText: "I feel stressed and frustrated about missing medications.",
  },
};

type InteractionType = keyof typeof INTERACTION_PRESETS;

interface InteractionFormProps {
  onSuccess: (data: CompanionInteractionApiResponse) => void;
  todayData: CompanionTodayApiResponse | undefined;
  isRefreshing: boolean;
  onRefresh: () => void;
}

export function InteractionForm({ onSuccess, todayData, isRefreshing, onRefresh }: InteractionFormProps) {
  const [interactionType, setInteractionType] = useState<InteractionType>("check_in");
  const [message, setMessage] = useState(INTERACTION_PRESETS.check_in.message);
  const [emotionText, setEmotionText] = useState(INTERACTION_PRESETS.check_in.emotionText);

  const mutation = useMutation({
    mutationFn: (payload: {
      interaction_type: InteractionType;
      message: string;
      emotion_text?: string;
    }) => runCompanionInteraction(payload),
    onSuccess: (data) => {
      onSuccess(data);
    },
  });

  const handleTypeChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const nextType = event.target.value as InteractionType;
    setInteractionType(nextType);
    setMessage(INTERACTION_PRESETS[nextType].message);
    setEmotionText(INTERACTION_PRESETS[nextType].emotionText);
  };

  const activePlan = todayData?.care_plan;

  return (
    <Card className="grain-overlay">
      <CardHeader>
        <CardTitle>Interactive Care Session</CardTitle>
        <CardDescription>
          Choose the interaction type, describe the barrier or question, and let the companion tailor the next step.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Button disabled={isRefreshing || mutation.isPending} onClick={onRefresh}>
            <AsyncLabel active={isRefreshing} idle="Refresh Today" loading="Refreshing" />
          </Button>
          {todayData && (
            <>
              <Badge variant={todayData.engagement.risk_level === "high" ? "default" : "outline"}>
                Risk: {todayData.engagement.risk_level}
              </Badge>
              <Badge variant="outline">Mode: {todayData.engagement.recommended_mode}</Badge>
              <Badge variant="outline">Policy: {todayData.care_plan.policy_status}</Badge>
            </>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="companion-interaction-type">Interaction Type</Label>
          <Select id="companion-interaction-type" value={interactionType} onChange={handleTypeChange}>
            {Object.entries(INTERACTION_PRESETS).map(([value, preset]) => (
              <option key={value} value={value}>
                {preset.label}
              </option>
            ))}
          </Select>
        </div>

        <div className="rounded-xl border border-[color:var(--border)] bg-white/70 p-4 dark:bg-[color:var(--panel-soft)]">
          <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">Today&apos;s Priority</div>
          <div className="mt-1 text-lg font-semibold">{activePlan?.headline ?? "Loading companion state…"}</div>
          <p className="app-muted mt-2 text-sm">{activePlan?.summary ?? "No care plan loaded yet."}</p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="companion-message">Patient Message</Label>
          <Textarea
            id="companion-message"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            rows={4}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="companion-emotion">Optional Emotional Context</Label>
          <Input
            id="companion-emotion"
            value={emotionText}
            onChange={(event) => setEmotionText(event.target.value)}
          />
        </div>
        <Button
          disabled={mutation.isPending || isRefreshing || !message.trim()}
          onClick={() =>
            mutation.mutate({
              interaction_type: interactionType,
              message,
              emotion_text: emotionText.trim() || undefined,
            })
          }
        >
          <AsyncLabel active={mutation.isPending} idle="Generate Next Step" loading="Thinking" />
        </Button>
      </CardContent>
    </Card>
  );
}
