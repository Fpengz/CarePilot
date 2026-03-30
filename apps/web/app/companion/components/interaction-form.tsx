"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
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

  return (
    <div className="bg-surface rounded-[1.8rem] overflow-hidden">
      <div className="px-8 py-6 border-b border-border-soft bg-panel/30">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h2 className="text-xl font-semibold tracking-tight text-foreground">Interaction Studio</h2>
            <p className="text-sm text-muted-foreground font-medium">
              Establish clinical intent and capture subjective patient context for reasoning.
            </p>
          </div>
          {todayData && (
            <Badge variant="outline" className="bg-accent-teal-muted text-accent-teal text-micro-label font-bold uppercase tracking-wider border-accent-teal/20 px-4 py-1 self-start sm:self-center">
              Mode: {todayData.engagement.recommended_mode}
            </Badge>
          )}
        </div>
      </div>

      <div className="p-8">
        <div className="grid gap-10 lg:grid-cols-2">
          {/* Left Column: Config */}
          <div className="space-y-8">
            <div className="space-y-3">
              <Label htmlFor="companion-interaction-type" className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground ml-1">
                Workflow Context
              </Label>
              <Select 
                id="companion-interaction-type" 
                value={interactionType} 
                onChange={handleTypeChange}
                className="h-12 rounded-2xl bg-panel border-border-soft focus:ring-accent-teal/20 shadow-sm transition-all text-sm font-medium"
              >
                {Object.entries(INTERACTION_PRESETS).map(([value, preset]) => (
                  <option key={value} value={value}>
                    {preset.label}
                  </option>
                ))}
              </Select>
            </div>

            <div className="space-y-3">
              <Label htmlFor="companion-emotion" className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground ml-1">
                Subjective Emotion (Optional)
              </Label>
              <div className="relative group">
                <Input
                  id="companion-emotion"
                  value={emotionText}
                  onChange={(event) => setEmotionText(event.target.value)}
                  className="h-12 pl-5 rounded-2xl bg-panel border-border-soft focus:ring-accent-teal/20 shadow-sm transition-all text-sm"
                  placeholder="e.g. Frustrated with adherence, anxious about diet..."
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2 flex gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                   <Badge variant="outline" className="text-[9px] cursor-pointer hover:bg-surface transition-colors border-border-soft">STRESSED</Badge>
                   <Badge variant="outline" className="text-[9px] cursor-pointer hover:bg-surface transition-colors border-border-soft">READY</Badge>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Narrative */}
          <div className="space-y-3">
            <div className="flex items-center justify-between ml-1">
              <Label htmlFor="companion-message" className="text-micro-label font-bold uppercase tracking-widest text-muted-foreground">
                Patient Narrative / Barriers
              </Label>
              <span className="text-[9px] font-bold text-accent-teal uppercase tracking-tighter opacity-60">Secure Channel</span>
            </div>
            <div className="relative rounded-3xl border border-border-soft bg-panel focus-within:ring-4 focus-within:ring-accent-teal/5 focus-within:border-accent-teal/30 transition-all overflow-hidden shadow-sm">
              <Textarea
                id="companion-message"
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                rows={6}
                className="border-none bg-transparent shadow-none focus-visible:ring-0 focus-visible:ring-offset-0 text-sm leading-relaxed p-6 resize-none"
                placeholder="Establish the clinical narrative here..."
              />
              <div className="absolute bottom-4 right-4">
                 <Button
                  className="rounded-2xl h-12 px-8 font-bold shadow-lg shadow-accent-teal/20 bg-accent-teal hover:bg-accent-teal/90 transition-all transform hover:scale-[1.02] active:scale-95 text-white"
                  disabled={mutation.isPending || isRefreshing || !message.trim()}
                  onClick={() =>
                    mutation.mutate({
                      interaction_type: interactionType,
                      message,
                      emotion_text: emotionText.trim() || undefined,
                    })
                  }
                >
                  <AsyncLabel active={mutation.isPending} idle="Generate Insight" loading="Synthesizing" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
