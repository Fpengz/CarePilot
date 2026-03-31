"use client";

import { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import type { MessageView } from "@/app/chat/components/types";
import { AssistantMeta } from "@/components/chat/assistant-meta";

const KIND_LABELS: Record<MessageView["kind"], string> = {
  proactive_alert: "Alert",
  meal_analysis: "Meal analysis",
  recommendation: "Recommendation",
  follow_up: "Follow-up",
  trend_insight: "Trend insight",
  plain: "",
};

const EMOJI: Record<string, string> = {
  happy: "😊",
  sad: "😢",
  angry: "😤",
  frustrated: "😩",
  anxious: "😰",
  neutral: "😐",
  confused: "😕",
  fearful: "😨",
};

export const MessageItem = memo(function MessageItem({
  message,
  isStreaming,
  streamDraft,
  onMealAction,
  proposalLoadingId,
}: {
  message: MessageView;
  isStreaming: boolean;
  streamDraft: string;
  onMealAction: (proposalId: string, action: "confirm" | "skip") => void;
  proposalLoadingId: string | null;
}) {
  const isUser = message.role === "user";
  const content = isStreaming ? `${message.content ?? ""}${streamDraft}` : message.content || "";

  if (isUser) {
    return (
      <div className="flex justify-end mb-6" style={{ contentVisibility: "auto", containIntrinsicSize: "0 80px" }}>
        <div className="max-w-[85%] rounded-2xl bg-accent-teal px-6 py-4 text-sm text-white shadow-sm ring-1 ring-accent-teal/10">
          <div className="whitespace-pre-wrap leading-relaxed font-medium">{message.content}</div>
          {message.emotion ? (
            <div className="mt-3 pt-3 border-t border-white/10 flex items-center gap-2 text-micro-label uppercase opacity-90">
              <span className="text-sm" aria-hidden="true">{EMOJI[message.emotion.label] ?? "🫥"}</span>
              <span className="sr-only">Detected emotion:</span>
              <span>{message.emotion.label}</span>
              <span className="opacity-60" aria-label={`${Math.round(message.emotion.score * 100)}% confidence`}>
                ({Math.round(message.emotion.score * 100)}%)
              </span>
            </div>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start mb-8" style={{ contentVisibility: "auto", containIntrinsicSize: "0 120px" }}>
      <div className="max-w-[90%] rounded-2xl border border-border-soft bg-surface px-6 py-6 shadow-sm">
        <AssistantMeta
          kindLabel={KIND_LABELS[message.kind] || undefined}
          confidence={message.confidence}
        />

        {message.title ? (
          <h4 className="mt-4 text-lg font-display font-semibold text-foreground tracking-tight">
            {message.title}
          </h4>
        ) : null}
        {message.explanation ? (
          <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
            {message.explanation}
          </p>
        ) : null}

        {content ? (
          <div className="chat-markdown mt-5 prose prose-sm prose-slate dark:prose-invert max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeSanitize]}
            >
              {content}
            </ReactMarkdown>
          </div>

        ) : isStreaming ? (
          <div className="mt-5 text-accent-teal animate-pulse font-bold">▋</div>
        ) : null}

        {message.reasoning ? (
          <div className="mt-6 rounded-2xl bg-panel border border-border-soft p-4">
            <div className="text-micro-label text-muted-foreground uppercase mb-2">
              Clinical Reasoning
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed italic">{message.reasoning}</p>
          </div>
        ) : null}

        {message.mealProposal ? (
          <div className="mt-6 pt-6 border-t border-border-soft flex flex-wrap gap-3">
            <button
              className="h-11 rounded-xl bg-accent-teal px-6 text-sm font-bold text-white shadow-sm transition-all hover:bg-accent-teal/90 disabled:opacity-60"
              onClick={() => onMealAction(message.mealProposal!.proposalId, "confirm")}
              disabled={proposalLoadingId === message.mealProposal.proposalId}
            >
              Log this meal
            </button>
            <button
              className="h-11 rounded-xl border border-border-soft bg-surface px-6 text-sm font-semibold text-foreground shadow-sm transition-all hover:bg-panel disabled:opacity-60"
              onClick={() => onMealAction(message.mealProposal!.proposalId, "skip")}
              disabled={proposalLoadingId === message.mealProposal.proposalId}
            >
              Skip
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
});
