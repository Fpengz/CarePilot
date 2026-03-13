import { type KeyboardEvent, type RefObject } from "react";

export type SuggestionChip = {
  id: string;
  label: string;
  value: string;
};

type ChatInputProps = {
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onKeyDown?: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  inputRef?: RefObject<HTMLTextAreaElement | null>;
  loading: boolean;
  suggestions?: SuggestionChip[];
  onSelectSuggestion?: (value: string) => void;
  onPrependTrack?: () => void;
  menuOpen: boolean;
  onToggleMenu: () => void;
  onStartRecording: () => void;
  isRecording: boolean;
  recordingLabel?: string;
  onStopRecording?: () => void;
  onCancelRecording?: () => void;
};

export function ChatInput({
  input,
  onInputChange,
  onSend,
  onKeyDown,
  inputRef,
  loading,
  suggestions = [],
  onSelectSuggestion,
  onPrependTrack,
  menuOpen,
  onToggleMenu,
  onStartRecording,
  isRecording,
  recordingLabel,
  onStopRecording,
  onCancelRecording,
}: ChatInputProps) {
  return (
    <div className="soft-block flex flex-col gap-3">
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {suggestions.map((chip) => (
            <button
              key={chip.id}
              type="button"
              className="min-h-[44px] rounded-full border border-[color:var(--border-soft)] px-4 py-2 text-xs font-semibold text-[color:var(--foreground)] hover:bg-[color:var(--muted)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--accent)]/40"
              onClick={() => onSelectSuggestion?.(chip.value)}
            >
              {chip.label}
            </button>
          ))}
        </div>
      )}

      {isRecording && (
        <div className="flex flex-wrap items-center gap-3 rounded-xl bg-red-50 px-3 py-2 text-red-600">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-red-500 animate-pulse" />
          <span className="text-sm font-mono">{recordingLabel ?? "00:00"}</span>
          <span className="text-xs flex-1">Recording…</span>
          <button
            type="button"
            aria-label="Cancel recording"
            onClick={onCancelRecording}
            className="min-h-[44px] text-xs text-red-300 hover:text-red-500 px-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-300/60"
          >
            ✕
          </button>
          <button
            type="button"
            aria-label="Stop and send recording"
            onClick={onStopRecording}
            className="min-h-[44px] text-xs px-4 py-2 rounded-full bg-red-500 text-white hover:bg-red-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-300/60"
          >
            ⏹ Stop &amp; Send
          </button>
        </div>
      )}

      <textarea
        ref={inputRef}
        value={input}
        onChange={(event) => onInputChange(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Ask anything… (Enter to send, Shift+Enter for new line)"
        rows={2}
        aria-label="Message input"
        className="w-full resize-none border-none bg-transparent outline-none text-sm text-[color:var(--foreground)] placeholder-[color:var(--muted-foreground)]"
      />

      <div className="flex items-center gap-2">
        <div className="relative z-50">
          <button
            type="button"
            onClick={onToggleMenu}
            aria-label="More options"
            className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-full border border-[color:var(--border-soft)] text-lg text-[color:var(--muted-foreground)] hover:bg-[color:var(--muted)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--accent)]/40"
          >
            ＋
          </button>
          {menuOpen && (
            <div className="absolute bottom-12 left-0 w-52 overflow-hidden rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--panel)] py-2 shadow-[0_10px_30px_rgba(15,23,42,0.08)]">
              <button
                type="button"
                onClick={onStartRecording}
                className="flex w-full items-center gap-3 px-4 py-3 text-left text-sm text-[color:var(--foreground)] hover:bg-[color:var(--muted)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--accent)]/40"
              >
                <span className="text-base">🎤</span>
                <span>Record Audio</span>
              </button>
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={onPrependTrack}
          aria-label="Add [TRACK] prefix"
          className="min-h-[44px] text-xs px-4 py-2 rounded-full border border-[color:var(--accent)]/40 text-[color:var(--accent)] hover:bg-[color:var(--accent)]/10 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--accent)]/40"
        >
          Add [TRACK]
        </button>
        <button
          type="button"
          onClick={onSend}
          disabled={loading || !input.trim()}
          aria-label="Send message"
          className="ml-auto min-h-[44px] text-sm font-medium px-4 py-2 rounded-full bg-[color:var(--accent)] text-[color:var(--accent-foreground)] hover:opacity-90 disabled:opacity-40 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--accent)]/40"
        >
          {loading ? "Thinking…" : "Send"}
        </button>
      </div>
    </div>
  );
}
