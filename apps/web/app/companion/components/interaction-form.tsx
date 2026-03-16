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
    <Card className="shadow-md rounded-[16px] overflow-hidden">
      <CardHeader className="bg-[color:var(--panel-soft)] border-b border-[color:var(--border-soft)] pb-4">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg font-bold text-[color:var(--foreground)]">Patient Interaction Studio</CardTitle>
            <CardDescription className="text-xs font-medium">
              Establish clinical intent and capture subjective patient context.
            </CardDescription>
          </div>
          {todayData && (
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="bg-[color:var(--surface)] text-[9px] font-bold uppercase tracking-tighter border-[color:var(--border-soft)]">
                Engagement: {todayData.engagement.recommended_mode}
              </Badge>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="p-6">
        <div className="grid gap-8 lg:grid-cols-2">
          {/* Left Column: Interaction Metadata */}
          <div className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="companion-interaction-type" className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">
                Workflow Context
              </Label>
              <Select 
                id="companion-interaction-type" 
                value={interactionType} 
                onChange={handleTypeChange}
                className="h-11 rounded-xl bg-[color:var(--panel-soft)] border-[color:var(--border-soft)] focus:ring-[color:var(--accent)]/40 shadow-sm transition-all"
              >
                {Object.entries(INTERACTION_PRESETS).map(([value, preset]) => (
                  <option key={value} value={value}>
                    {preset.label}
                  </option>
                ))}
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="companion-emotion" className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">
                Subjective Emotion (Optional)
              </Label>
              <div className="relative group">
                <Input
                  id="companion-emotion"
                  value={emotionText}
                  onChange={(event) => setEmotionText(event.target.value)}
                  className="h-11 pl-4 rounded-xl bg-[color:var(--panel-soft)] border-[color:var(--border-soft)] focus:ring-[color:var(--accent)]/40 shadow-sm transition-all text-sm"
                  placeholder="e.g. Frustrated with adherence, anxious about diet..."
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                   <Badge variant="outline" className="text-[8px] cursor-pointer hover:bg-[color:var(--panel-soft)]">Stressed</Badge>
                   <Badge variant="outline" className="text-[8px] cursor-pointer hover:bg-[color:var(--panel-soft)]">Ready</Badge>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Narrative Input */}
          <div className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="companion-message" className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">
                  Patient Narrative / Barrier
                </Label>
                <span className="text-[9px] font-bold text-[color:var(--muted-foreground)] uppercase">Secure Clinical Channel</span>
              </div>
              <div className="relative rounded-[16px] border border-[color:var(--border-soft)] bg-[color:var(--panel-soft)] focus-within:ring-2 focus-within:ring-[color:var(--accent)]/30 focus-within:border-[color:var(--accent)] transition-all overflow-hidden shadow-inner">
                <Textarea
                  id="companion-message"
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  rows={5}
                  className="border-none bg-transparent shadow-none focus-visible:ring-0 focus-visible:ring-offset-0 text-sm leading-relaxed p-4 resize-none"
                  placeholder="Establish the clinical narrative here..."
                />
                <div className="absolute bottom-3 right-3 flex items-center gap-3">
                   <Button
                    size="sm"
                    className="rounded-full h-10 px-6 font-bold shadow-lg shadow-[color:var(--accent)]/25 bg-[color:var(--accent)] hover:bg-[color:var(--accent)]/90 transition-all transform hover:scale-[1.02] active:scale-[0.98]"
                    disabled={mutation.isPending || isRefreshing || !message.trim()}
                    onClick={() =>
                      mutation.mutate({
                        interaction_type: interactionType,
                        message,
                        emotion_text: emotionText.trim() || undefined,
                      })
                    }
                  >
                    <AsyncLabel active={mutation.isPending} idle="Generate Decision" loading="Thinking" />
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
