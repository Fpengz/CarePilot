"use client";

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

export function MessageItem({
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
      <div className="flex justify-end">
        <div className="max-w-[78%] rounded-2xl bg-[color:var(--accent)] px-5 py-4 text-sm text-[color:var(--accent-foreground)] shadow-[0_12px_24px_rgba(15,23,42,0.1)]">
          <div className="whitespace-pre-wrap leading-relaxed">{message.content}</div>
          {message.emotion ? (
            <div className="mt-3 flex items-center gap-2 text-xs uppercase tracking-[0.16em] opacity-80">
              <span>{EMOJI[message.emotion.label] ?? "🫥"}</span>
              <span className="capitalize">{message.emotion.label}</span>
              <span className="opacity-60">({Math.round(message.emotion.score * 100)}%)</span>
            </div>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[82%] rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] px-6 py-5">
        <AssistantMeta
          kindLabel={KIND_LABELS[message.kind] || undefined}
          confidence={message.confidence}
        />

        {message.title ? (
          <h4 className="mt-3 text-base font-semibold text-[color:var(--foreground)]">
            {message.title}
          </h4>
        ) : null}
        {message.explanation ? (
          <p className="mt-2 text-sm text-[color:var(--muted-foreground)]">
            {message.explanation}
          </p>
        ) : null}

        {content ? (
          <ReactMarkdown
            className="chat-markdown mt-4"
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeSanitize]}
          >
            {content}
          </ReactMarkdown>
        ) : isStreaming ? (
          <div className="mt-4 text-sm text-[color:var(--muted-foreground)] animate-pulse">▋</div>
        ) : null}

        {message.reasoning ? (
          <div className="mt-4 rounded-xl bg-[color:var(--panel-soft)] px-4 py-3">
            <div className="text-[0.7rem] font-semibold uppercase tracking-[0.2em] text-[color:var(--muted-foreground)]">
              Reasoning
            </div>
            <p className="mt-2 text-sm text-[color:var(--muted-foreground)]">{message.reasoning}</p>
          </div>
        ) : null}

        {message.mealProposal ? (
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              className="min-h-[44px] rounded-full bg-[color:var(--accent)] px-4 py-2 text-xs font-semibold text-[color:var(--accent-foreground)] disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--accent)]/40"
              onClick={() => onMealAction(message.mealProposal!.proposalId, "confirm")}
              disabled={proposalLoadingId === message.mealProposal.proposalId}
            >
              Log meal
            </button>
            <button
              className="min-h-[44px] rounded-full border border-[color:var(--border-soft)] px-4 py-2 text-xs font-semibold text-[color:var(--foreground)] disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--accent)]/40"
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
}
