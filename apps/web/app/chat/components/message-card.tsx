"use client";

import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import { MessageView } from "./types";

const KIND_LABELS: Record<MessageView["kind"], string> = {
  proactive_alert: "Proactive alert",
  meal_analysis: "Meal analysis",
  recommendation: "Recommendation",
  follow_up: "Follow-up",
  trend_insight: "Trend insight",
  plain: "Assistant",
};

const KIND_TONES: Record<MessageView["kind"], string> = {
  proactive_alert: "text-rose-700 bg-rose-50 border-rose-100",
  meal_analysis: "text-emerald-700 bg-emerald-50 border-emerald-100",
  recommendation: "text-slate-700 bg-slate-50 border-slate-100",
  follow_up: "text-amber-700 bg-amber-50 border-amber-100",
  trend_insight: "text-indigo-700 bg-indigo-50 border-indigo-100",
  plain: "text-slate-700 bg-slate-50 border-slate-100",
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

function MessageKindBadge({ kind }: { kind: MessageView["kind"] }) {
  const tone = KIND_TONES[kind];
  return (
    <div
      className={`rounded-full border px-3 py-1 text-[0.7rem] font-semibold uppercase tracking-[0.2em] ${tone}`}
      aria-label={`Message type: ${KIND_LABELS[kind]}`}
    >
      {KIND_LABELS[kind]}
    </div>
  );
}

function ConfidenceMeter({ value }: { value?: number }) {
  if (value === undefined) return null;
  const pct = Math.round(value * 100);
  return (
    <div
      className="flex items-center gap-3 text-xs text-[color:var(--muted-foreground)]"
      aria-label={`Confidence ${pct}%`}
    >
      <div className="h-1.5 w-24 rounded-full bg-[color:var(--border-soft)] overflow-hidden">
        <div
          className="h-full rounded-full bg-[color:var(--accent)]"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="tabular-nums">{pct}% confidence</span>
    </div>
  );
}

export function MessageCard({
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
  const reasoning = message.reasoning;
  const content = message.content || (isStreaming ? streamDraft : "");

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[78%] rounded-2xl bg-[color:var(--accent)] px-5 py-4 text-sm text-[color:var(--accent-foreground)] shadow-[0_18px_36px_rgba(15,23,42,0.12)]">
          <div className="whitespace-pre-wrap leading-relaxed">{message.content}</div>
          {message.emotion && (
            <div className="mt-3 flex items-center gap-2 text-xs uppercase tracking-[0.16em] opacity-80">
              <span>{EMOJI[message.emotion.label] ?? "🫥"}</span>
              <span className="capitalize">{message.emotion.label}</span>
              <span className="opacity-60">({Math.round(message.emotion.score * 100)}%)</span>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[82%] rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] px-6 py-5 shadow-[0_16px_32px_rgba(15,23,42,0.06)]">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <MessageKindBadge kind={message.kind} />
          <ConfidenceMeter value={message.confidence} />
        </div>

        {message.title && (
          <h4 className="mt-4 text-base font-semibold text-[color:var(--foreground)]">
            {message.title}
          </h4>
        )}
        {message.explanation && (
          <p className="mt-2 text-sm text-[color:var(--muted-foreground)]">
            {message.explanation}
          </p>
        )}

        {content ? (
          <ReactMarkdown className="chat-markdown mt-4" rehypePlugins={[rehypeSanitize]}>
            {content}
          </ReactMarkdown>
        ) : isStreaming ? (
          <div className="mt-4 text-sm text-[color:var(--muted-foreground)] animate-pulse">▋</div>
        ) : null}

        {reasoning && (
          <div className="mt-4 rounded-xl bg-[color:var(--panel-soft)] px-4 py-3">
            <div className="text-[0.7rem] font-semibold uppercase tracking-[0.2em] text-[color:var(--muted-foreground)]">
              Reasoning
            </div>
            <p className="mt-2 text-sm text-[color:var(--muted-foreground)]">{reasoning}</p>
          </div>
        )}

        {message.mealProposal && (
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
        )}
      </div>
    </div>
  );
}
