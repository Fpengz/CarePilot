"use client";

import { MessageItem } from "@/components/chat/message-item";
import type { MessageView } from "@/app/chat/components/types";

export function MessageList({
  messages,
  streamDraft,
  loading,
  streamNotice,
  audioNotice,
  onMealAction,
  proposalLoadingId,
  bottomRef,
}: {
  messages: MessageView[];
  streamDraft: string;
  loading: boolean;
  streamNotice: string | null;
  audioNotice: string | null;
  onMealAction: (proposalId: string, action: "confirm" | "skip") => void;
  proposalLoadingId: string | null;
  bottomRef: React.RefObject<HTMLDivElement | null>;
}) {
  return (
    <div className="flex-1 space-y-4 overflow-y-auto pb-6">
      {(streamNotice || audioNotice) && (
        <div className="space-y-2" role="status" aria-live="polite">
          {streamNotice ? (
            <div className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--panel)] px-4 py-3 text-sm text-[color:var(--foreground)]">
              <div className="text-xs font-semibold uppercase tracking-[0.2em] text-[color:var(--muted-foreground)]">
                Stream notice
              </div>
              <div className="mt-2">{streamNotice}</div>
            </div>
          ) : null}
          {audioNotice ? (
            <div className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--panel)] px-4 py-3 text-sm text-[color:var(--foreground)]">
              <div className="text-xs font-semibold uppercase tracking-[0.2em] text-[color:var(--muted-foreground)]">
                Audio notice
              </div>
              <div className="mt-2">{audioNotice}</div>
            </div>
          ) : null}
        </div>
      )}

      {messages.map((message, index) => {
        const isStreamingMessage =
          message.role === "assistant" && index === messages.length - 1 && loading;
        return (
          <MessageItem
            key={message.id}
            message={message}
            isStreaming={isStreamingMessage}
            streamDraft={isStreamingMessage ? streamDraft : ""}
            onMealAction={onMealAction}
            proposalLoadingId={proposalLoadingId}
          />
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
